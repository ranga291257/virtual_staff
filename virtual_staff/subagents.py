from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List

from dwsim_integration_starter import CandidateSettings, DWSIMRunner, HeaterInputs
from fired_heater_calcs import CombustionBasis, ProcessBasis, solve_fired_heater
from fired_heater_control import run_closed_loop_demo
from virtual_staff.contracts import AgentRole, HandoffRequest, HandoffResponse
from virtual_staff.dwsim_pythonnet_runner import DWSIMPythonnetRunner


class ProcessOptSubagent:
    role = AgentRole.PROCESS_OPT_SUBAGENT

    def run(self, request: HandoffRequest) -> HandoffResponse:
        heater = request.context["heater_state"]
        base_excess_air = float(request.context.get("constraints", {}).get("base_excess_air_fraction", 0.10))
        candidates: List[Dict[str, float]] = [
            {"excess_air_fraction": max(base_excess_air - 0.02, 0.02), "stack_temp_c": 240.0},
            {"excess_air_fraction": base_excess_air, "stack_temp_c": 250.0},
            {"excess_air_fraction": min(base_excess_air + 0.03, 0.30), "stack_temp_c": 260.0},
        ]
        output = {
            "heater_id": heater["heater_id"],
            "candidate_settings": candidates,
            "expected_kpi_delta": {"fuel_saving_pct_range": [0.5, 1.8]},
        }
        return HandoffResponse(
            request_id=request.request_id,
            role=self.role,
            success=True,
            output=output,
            artifacts={},
            evidence=["candidate grid around excess air", "base process constraints used"],
        )


class MaintenanceSubagent:
    role = AgentRole.MAINTENANCE_SUBAGENT

    def run(self, request: HandoffRequest) -> HandoffResponse:
        stack_temp_c = float(request.context.get("heater_state", {}).get("stack_temp_c", 250.0))
        derate = 0.10 if stack_temp_c > 280.0 else 0.0
        output = {
            "maintenance_constraints": {
                "max_fired_duty_derate_fraction": derate,
                "next_inspection_window_hours": 72,
            },
            "recommended_actions": [
                "verify burner tile condition",
                "check stack O2 analyzer calibration",
            ],
        }
        return HandoffResponse(
            request_id=request.request_id,
            role=self.role,
            success=True,
            output=output,
            artifacts={},
            evidence=["stack temperature trend screening", "preventive actions emitted"],
        )


class SimRunnerSubagent:
    role = AgentRole.SIM_RUNNER_SUBAGENT

    def __init__(self, runner: DWSIMRunner | None = None):
        self.runner = runner or DWSIMRunner()
        self.pythonnet_runner = DWSIMPythonnetRunner(starter_runner=self.runner)

    def _evaluate_with_calcs(self, heater_inputs: Dict[str, float], candidate: Dict[str, float]) -> Dict[str, float]:
        pb = ProcessBasis(
            mass_flow_kg_s=heater_inputs["feed_flow_kg_s"],
            inlet_temp_c=heater_inputs["feed_inlet_temp_c"],
            outlet_temp_c=heater_inputs["target_outlet_temp"],
            cp_kj_kg_k=heater_inputs.get("cp_kj_kg_k", 2.5),
            density_kg_m3=heater_inputs.get("density_kg_m3", 800.0),
        )
        cb = CombustionBasis(
            excess_air_fraction=candidate["excess_air_fraction"],
            stack_temp_c=candidate["stack_temp_c"],
        )
        solved = solve_fired_heater(pb, cb)
        out = asdict(solved)
        out["candidate"] = candidate
        return out

    def run(self, request: HandoffRequest) -> HandoffResponse:
        heater_inputs = request.context["heater_state"]
        candidate = request.context["candidate"]
        case_name = request.context.get("case_name", "virtual_staff_case")
        output: Dict[str, float]
        artifacts: Dict[str, str] = {}

        try:
            heater = HeaterInputs(
                heater_id=heater_inputs["heater_id"],
                feed_flow_kg_s=heater_inputs["feed_flow_kg_s"],
                feed_inlet_temp_c=heater_inputs["feed_inlet_temp_c"],
                target_outlet_temp=heater_inputs["target_outlet_temp"],
                cp_kj_kg_k=heater_inputs.get("cp_kj_kg_k", 2.5),
                density_kg_m3=heater_inputs.get("density_kg_m3", 800.0),
                process_pressure_barg=heater_inputs.get("process_pressure_barg", 10.0),
                tube_dp_bar=heater_inputs.get("tube_dp_bar", 1.5),
            )
            settings = CandidateSettings(
                excess_air_fraction=candidate["excess_air_fraction"],
                stack_temp_c=candidate["stack_temp_c"],
            )
            pythonnet_out = self.pythonnet_runner.run_case(case_name=case_name, heater_inputs=heater, candidate=settings)
            if pythonnet_out.get("run_status") != "success":
                raise RuntimeError(pythonnet_out.get("error", "DWSIM run failed."))
            output = dict(pythonnet_out.get("raw_results", {}))
            output["runtime_mode"] = pythonnet_out.get("mode", "unknown")
            # Attach compact control sanity trace to keep operability context in each candidate.
            control_trace = run_closed_loop_demo(steps=4, disturbance_step=2, inlet_temp_drop_c=5.0)
            output["control_preview"] = control_trace
            artifacts = dict(pythonnet_out.get("artifacts", {}))
        except Exception:
            output = self._evaluate_with_calcs(heater_inputs=heater_inputs, candidate=candidate)
            output["runtime_mode"] = "calc_fallback"

        return HandoffResponse(
            request_id=request.request_id,
            role=self.role,
            success=True,
            output=output,
            artifacts=artifacts,
            evidence=["dwsim runner attempted", "fallback to deterministic calc available"],
        )


class SafetyAuditSubagent:
    role = AgentRole.SAFETY_AUDIT_SUBAGENT

    def run(self, request: HandoffRequest) -> HandoffResponse:
        constraints = request.context.get("safety_constraints", {})
        candidate = request.context.get("candidate", {})
        reasons: List[str] = []

        if candidate.get("stack_temp_c", 0.0) > constraints.get("max_stack_temp_c", 350.0):
            reasons.append("stack temperature exceeds policy")
        if candidate.get("excess_air_fraction", 0.0) < constraints.get("min_excess_air_fraction", 0.02):
            reasons.append("excess air below policy")

        output = {"audit_passed": len(reasons) == 0, "reasons": reasons}
        return HandoffResponse(
            request_id=request.request_id,
            role=self.role,
            success=True,
            output=output,
            artifacts={},
            evidence=["deterministic policy check"],
            errors=[] if len(reasons) == 0 else reasons,
        )
