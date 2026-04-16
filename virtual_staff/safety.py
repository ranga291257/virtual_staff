from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from virtual_staff.contracts import ActionIntent, RiskClass


AUTONOMY_MATRIX = {
    "read_only_analysis": {"max_risk": "high", "mode": "auto"},
    "candidate_evaluation": {"max_risk": "high", "mode": "auto_with_safety_gate"},
    "recommendation_publish": {"max_risk": "medium", "mode": "guarded_auto"},
    "work_order_prepare": {"max_risk": "medium", "mode": "guarded_auto"},
    "ot_write_request": {"max_risk": "low", "mode": "human_ack_required"},
}


@dataclass
class SafetyPolicy:
    max_excess_air_fraction: float = 0.30
    min_excess_air_fraction: float = 0.02
    max_stack_temp_c: float = 350.0
    min_stack_temp_c: float = 120.0
    min_confidence: float = 0.55
    forbidden_destinations: List[str] = None

    def __post_init__(self) -> None:
        if self.forbidden_destinations is None:
            self.forbidden_destinations = ["bms_write", "sis_write", "dcs_direct_write"]


@dataclass
class SafetyEvaluation:
    accepted: bool
    reasons: List[str]
    autonomy_tier: str
    sanitized_parameters: Dict[str, float]


class DeterministicSafetyGate:
    def __init__(self, policy: SafetyPolicy | None = None):
        self.policy = policy or SafetyPolicy()

    def autonomy_tier_for(self, intent: ActionIntent) -> str:
        if intent.risk_class in (RiskClass.CRITICAL, RiskClass.HIGH):
            return "tier_3_human_ack_required"
        if intent.risk_class == RiskClass.MEDIUM:
            return "tier_2_guarded_auto"
        return "tier_1_auto"

    def evaluate(self, intent: ActionIntent) -> SafetyEvaluation:
        reasons: List[str] = []
        params = dict(intent.parameters)

        if intent.confidence < self.policy.min_confidence:
            reasons.append(f"confidence {intent.confidence:.2f} below minimum {self.policy.min_confidence:.2f}")

        for dest in intent.forbidden_destinations:
            if dest in self.policy.forbidden_destinations:
                reasons.append(f"forbidden destination requested: {dest}")
        execution_destination = str(params.get("execution_destination", "local_advisory"))
        if execution_destination in self.policy.forbidden_destinations:
            reasons.append(f"execution_destination blocked by policy: {execution_destination}")

        excess_air = float(params.get("excess_air_fraction", 0.10))
        if excess_air < self.policy.min_excess_air_fraction or excess_air > self.policy.max_excess_air_fraction:
            reasons.append(
                "excess_air_fraction out of bounds "
                f"({self.policy.min_excess_air_fraction:.2f}-{self.policy.max_excess_air_fraction:.2f})"
            )
            excess_air = min(max(excess_air, self.policy.min_excess_air_fraction), self.policy.max_excess_air_fraction)

        stack_temp = float(params.get("stack_temp_c", 250.0))
        if stack_temp < self.policy.min_stack_temp_c or stack_temp > self.policy.max_stack_temp_c:
            reasons.append(
                "stack_temp_c out of bounds "
                f"({self.policy.min_stack_temp_c:.1f}-{self.policy.max_stack_temp_c:.1f})"
            )
            stack_temp = min(max(stack_temp, self.policy.min_stack_temp_c), self.policy.max_stack_temp_c)

        params["excess_air_fraction"] = excess_air
        params["stack_temp_c"] = stack_temp
        accepted = len(reasons) == 0
        tier = self.autonomy_tier_for(intent)

        return SafetyEvaluation(
            accepted=accepted,
            reasons=reasons,
            autonomy_tier=tier,
            sanitized_parameters=params,
        )
