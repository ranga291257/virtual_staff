from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class AgentRole(str, Enum):
    PROCESS_ENGINEER = "process_engineer"
    MAINTENANCE_ENGINEER = "maintenance_engineer"
    ORCHESTRATOR = "orchestrator"
    PROCESS_OPT_SUBAGENT = "process_opt_subagent"
    MAINTENANCE_SUBAGENT = "maintenance_subagent"
    SIM_RUNNER_SUBAGENT = "sim_runner_subagent"
    SAFETY_AUDIT_SUBAGENT = "safety_audit_subagent"


class RiskClass(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ActionIntent:
    action_type: str
    target: str
    parameters: Dict[str, Any]
    expected_artifacts: List[str]
    risk_class: RiskClass
    confidence: float
    evidence: List[str]
    forbidden_destinations: List[str] = field(default_factory=list)


@dataclass
class HandoffRequest:
    request_id: str
    parent_request_id: Optional[str]
    role: AgentRole
    intent: ActionIntent
    context: Dict[str, Any]
    timeout_seconds: int = 30
    retry_limit: int = 2
    created_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def new(
        cls,
        role: AgentRole,
        intent: ActionIntent,
        context: Dict[str, Any],
        parent_request_id: Optional[str] = None,
        timeout_seconds: int = 30,
        retry_limit: int = 2,
    ) -> "HandoffRequest":
        return cls(
            request_id=str(uuid4()),
            parent_request_id=parent_request_id,
            role=role,
            intent=intent,
            context=context,
            timeout_seconds=timeout_seconds,
            retry_limit=retry_limit,
        )


@dataclass
class HandoffResponse:
    request_id: str
    role: AgentRole
    success: bool
    output: Dict[str, Any]
    artifacts: Dict[str, str]
    evidence: List[str]
    errors: List[str] = field(default_factory=list)
    elapsed_ms: int = 0
    completed_at: str = field(default_factory=utc_now_iso)


@dataclass
class SharedMemory:
    heater_state: Dict[str, Any]
    last_accepted_recommendation: Optional[Dict[str, Any]] = None
    active_maintenance_constraints: Dict[str, Any] = field(default_factory=dict)
    unresolved_conflicts: List[Dict[str, Any]] = field(default_factory=list)


ROLE_CONTRACTS: Dict[AgentRole, Dict[str, Any]] = {
    AgentRole.PROCESS_ENGINEER: {
        "description": "Generates operation candidates with KPI delta expectations.",
        "required_inputs": [
            "heater_state",
            "objective",
            "constraints",
            "maintenance_constraints",
        ],
        "required_outputs": [
            "candidate_settings",
            "expected_kpi_delta",
            "risk_class",
            "confidence",
        ],
        "required_evidence": [
            "calculation_basis",
            "constraint_check_summary",
        ],
    },
    AgentRole.MAINTENANCE_ENGINEER: {
        "description": "Maintains reliability constraints and work-prep actions.",
        "required_inputs": [
            "heater_state",
            "asset_condition",
            "recent_failures",
        ],
        "required_outputs": [
            "maintenance_constraints",
            "recommended_actions",
            "risk_class",
            "confidence",
        ],
        "required_evidence": [
            "inspection_signal",
            "degradation_indicator",
        ],
    },
    AgentRole.ORCHESTRATOR: {
        "description": "Coordinates role handoff, resolves conflicts, and publishes action package.",
        "required_inputs": [
            "process_candidates",
            "maintenance_constraints",
            "safety_validation",
            "simulation_results",
        ],
        "required_outputs": [
            "selected_action",
            "ranked_options",
            "rollback_note",
        ],
        "required_evidence": [
            "ranking_logic",
            "safety_gate_result",
            "sim_result_reference",
        ],
    },
}


HANDOFF_REQUEST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["request_id", "role", "intent", "context", "created_at"],
    "properties": {
        "request_id": {"type": "string"},
        "parent_request_id": {"type": ["string", "null"]},
        "role": {"type": "string"},
        "intent": {
            "type": "object",
            "required": [
                "action_type",
                "target",
                "parameters",
                "expected_artifacts",
                "risk_class",
                "confidence",
                "evidence",
            ],
            "properties": {
                "action_type": {"type": "string"},
                "target": {"type": "string"},
                "parameters": {"type": "object"},
                "expected_artifacts": {"type": "array", "items": {"type": "string"}},
                "risk_class": {"type": "string"},
                "confidence": {"type": "number"},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "forbidden_destinations": {"type": "array", "items": {"type": "string"}},
            },
        },
        "context": {"type": "object"},
        "timeout_seconds": {"type": "integer"},
        "retry_limit": {"type": "integer"},
        "created_at": {"type": "string"},
    },
}


HANDOFF_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": [
        "request_id",
        "role",
        "success",
        "output",
        "artifacts",
        "evidence",
        "completed_at",
    ],
    "properties": {
        "request_id": {"type": "string"},
        "role": {"type": "string"},
        "success": {"type": "boolean"},
        "output": {"type": "object"},
        "artifacts": {"type": "object"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "errors": {"type": "array", "items": {"type": "string"}},
        "completed_at": {"type": "string"},
    },
}
