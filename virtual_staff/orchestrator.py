from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import asdict
import time
from typing import Any, Dict, List, Tuple

from virtual_staff.contracts import (
    ActionIntent,
    AgentRole,
    HandoffRequest,
    HandoffResponse,
    RiskClass,
    SharedMemory,
)
from virtual_staff.event_store import OpsEventStore
from virtual_staff.safety import DeterministicSafetyGate
from virtual_staff.subagents import (
    MaintenanceSubagent,
    ProcessOptSubagent,
    SafetyAuditSubagent,
    SimRunnerSubagent,
)


class OrchestratorAgent:
    def __init__(self, event_store: OpsEventStore | None = None):
        self.event_store = event_store or OpsEventStore()
        self.process_subagent = ProcessOptSubagent()
        self.maintenance_subagent = MaintenanceSubagent()
        self.sim_subagent = SimRunnerSubagent()
        self.safety_audit_subagent = SafetyAuditSubagent()
        self.safety_gate = DeterministicSafetyGate()

    def _call_with_retry(self, subagent: Any, request: HandoffRequest) -> HandoffResponse:
        attempts = 0
        last_error = ""
        while attempts <= request.retry_limit:
            attempts += 1
            t0 = time.time()
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(subagent.run, request)
                    response = future.result(timeout=request.timeout_seconds)
                response.elapsed_ms = int((time.time() - t0) * 1000)
                if response.success:
                    self.event_store.append("handoff_success", asdict(response))
                    return response
                last_error = "; ".join(response.errors) if response.errors else "unknown subagent failure"
            except FutureTimeoutError:
                last_error = f"timeout after {request.timeout_seconds}s"
                self.event_store.append(
                    "handoff_timeout",
                    {
                        "request_id": request.request_id,
                        "role": request.role.value,
                        "attempt": attempts,
                        "timeout_seconds": request.timeout_seconds,
                    },
                )
            except Exception as exc:
                last_error = str(exc)
            self.event_store.append(
                "handoff_retry",
                {
                    "request_id": request.request_id,
                    "role": request.role.value,
                    "attempt": attempts,
                    "error": last_error,
                },
            )

        return HandoffResponse(
            request_id=request.request_id,
            role=request.role,
            success=False,
            output={},
            artifacts={},
            evidence=[],
            errors=[f"retry exhausted: {last_error}"],
            elapsed_ms=0,
        )

    def _score_candidate(self, sim_output: Dict[str, Any]) -> float:
        methane = float(sim_output.get("methane_kg_s", 1e9))
        efficiency = float(sim_output.get("efficiency", sim_output.get("efficiency_est", 0.0)))
        stack_loss = float(sim_output.get("stack_loss_kw", 1e9))
        return (efficiency * 1000.0) - (methane * 100.0) - (stack_loss * 0.01)

    def _prepare_process_request(self, memory: SharedMemory) -> HandoffRequest:
        intent = ActionIntent(
            action_type="generate_candidates",
            target=memory.heater_state["heater_id"],
            parameters={"objective": "minimize_fuel_while_meeting_outlet_temp"},
            expected_artifacts=["candidate_settings", "expected_kpi_delta"],
            risk_class=RiskClass.MEDIUM,
            confidence=0.80,
            evidence=["objective statement", "base constraints"],
        )
        return HandoffRequest.new(
            role=AgentRole.PROCESS_OPT_SUBAGENT,
            intent=intent,
            context={
                "heater_state": memory.heater_state,
                "constraints": {"base_excess_air_fraction": 0.10},
                "maintenance_constraints": memory.active_maintenance_constraints,
            },
        )

    def _prepare_maintenance_request(self, memory: SharedMemory) -> HandoffRequest:
        intent = ActionIntent(
            action_type="derive_maintenance_constraints",
            target=memory.heater_state["heater_id"],
            parameters={},
            expected_artifacts=["maintenance_constraints", "recommended_actions"],
            risk_class=RiskClass.MEDIUM,
            confidence=0.75,
            evidence=["trend signal"],
        )
        return HandoffRequest.new(
            role=AgentRole.MAINTENANCE_SUBAGENT,
            intent=intent,
            context={"heater_state": memory.heater_state, "asset_condition": "nominal", "recent_failures": []},
        )

    def run_cycle(self, memory: SharedMemory, case_name: str = "virtual_staff_cycle") -> Dict[str, Any]:
        self.event_store.append("cycle_start", {"heater_id": memory.heater_state["heater_id"]})

        maintenance_req = self._prepare_maintenance_request(memory)
        maintenance_resp = self._call_with_retry(self.maintenance_subagent, maintenance_req)
        if not maintenance_resp.success:
            raise RuntimeError(f"maintenance subagent failed: {maintenance_resp.errors}")
        memory.active_maintenance_constraints = maintenance_resp.output.get("maintenance_constraints", {})

        process_req = self._prepare_process_request(memory)
        process_resp = self._call_with_retry(self.process_subagent, process_req)
        if not process_resp.success:
            raise RuntimeError(f"process subagent failed: {process_resp.errors}")

        candidates: List[Dict[str, float]] = process_resp.output.get("candidate_settings", [])
        ranked: List[Tuple[float, Dict[str, Any]]] = []
        rejected: List[Dict[str, Any]] = []

        for idx, candidate in enumerate(candidates):
            intent = ActionIntent(
                action_type="evaluate_candidate",
                target=memory.heater_state["heater_id"],
                parameters=candidate,
                expected_artifacts=["sim_output"],
                risk_class=RiskClass.MEDIUM,
                confidence=0.70,
                evidence=["candidate generated by process optimizer"],
                forbidden_destinations=[],
            )
            gate = self.safety_gate.evaluate(intent)
            if not gate.accepted:
                rejected.append({"candidate": candidate, "reasons": gate.reasons, "tier": gate.autonomy_tier})
                self.event_store.append("candidate_rejected", rejected[-1])
                continue

            audit_req = HandoffRequest.new(
                role=AgentRole.SAFETY_AUDIT_SUBAGENT,
                intent=intent,
                context={
                    "candidate": gate.sanitized_parameters,
                    "safety_constraints": {
                        "max_stack_temp_c": self.safety_gate.policy.max_stack_temp_c,
                        "min_excess_air_fraction": self.safety_gate.policy.min_excess_air_fraction,
                    },
                },
            )
            audit_resp = self._call_with_retry(self.safety_audit_subagent, audit_req)
            if not audit_resp.success or not audit_resp.output.get("audit_passed", False):
                rejected.append(
                    {
                        "candidate": candidate,
                        "reasons": audit_resp.output.get("reasons", audit_resp.errors),
                        "tier": gate.autonomy_tier,
                    }
                )
                self.event_store.append("candidate_rejected", rejected[-1])
                continue

            sim_req = HandoffRequest.new(
                role=AgentRole.SIM_RUNNER_SUBAGENT,
                intent=intent,
                context={
                    "heater_state": memory.heater_state,
                    "candidate": gate.sanitized_parameters,
                    "case_name": f"{case_name}_{idx}",
                },
            )
            sim_resp = self._call_with_retry(self.sim_subagent, sim_req)
            if not sim_resp.success:
                rejected.append({"candidate": candidate, "reasons": sim_resp.errors, "tier": gate.autonomy_tier})
                self.event_store.append("candidate_rejected", rejected[-1])
                continue

            derate = float(memory.active_maintenance_constraints.get("max_fired_duty_derate_fraction", 0.0))
            max_fired_duty_kw = 11_500.0 * (1.0 - derate)
            fired_duty_kw = float(sim_resp.output.get("fired_duty_kw", 0.0))
            if fired_duty_kw > max_fired_duty_kw:
                rejected.append(
                    {
                        "candidate": candidate,
                        "reasons": [
                            "maintenance constraint conflict: fired duty exceeds derated limit",
                            f"fired_duty_kw={fired_duty_kw:.1f} > max_allowed_kw={max_fired_duty_kw:.1f}",
                        ],
                        "tier": gate.autonomy_tier,
                    }
                )
                self.event_store.append("candidate_rejected", rejected[-1])
                continue

            score = self._score_candidate(sim_resp.output)
            ranked.append(
                (
                    score,
                    {
                        "candidate": gate.sanitized_parameters,
                        "sim_output": sim_resp.output,
                        "artifacts": sim_resp.artifacts,
                        "score": score,
                        "autonomy_tier": gate.autonomy_tier,
                    },
                )
            )

        ranked.sort(key=lambda x: x[0], reverse=True)
        selected = ranked[0][1] if ranked else None

        action_package = {
            "selected_action": selected,
            "ranked_options": [item[1] for item in ranked],
            "rejected_options": rejected,
            "rollback_note": "Revert to last accepted recommendation and advisory mode on validation failure.",
            "maintenance_actions": maintenance_resp.output.get("recommended_actions", []),
        }
        memory.last_accepted_recommendation = selected

        self.event_store.append("cycle_complete", action_package)
        return action_package


def default_memory() -> SharedMemory:
    return SharedMemory(
        heater_state={
            "heater_id": "FH-101",
            "feed_flow_kg_s": 100.0,
            "feed_inlet_temp_c": 260.0,
            "target_outlet_temp": 300.0,
            "cp_kj_kg_k": 2.5,
            "density_kg_m3": 800.0,
            "process_pressure_barg": 10.0,
            "tube_dp_bar": 1.5,
            "stack_temp_c": 250.0,
        }
    )
