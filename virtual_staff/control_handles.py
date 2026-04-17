from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MVHandlePolicy:
    min_value: float
    max_value: float
    max_step_delta: float


MV_POLICIES = {
    "mv.fuel_valve_open_pct": MVHandlePolicy(min_value=5.0, max_value=95.0, max_step_delta=8.0),
    "mv.air_valve_open_pct": MVHandlePolicy(min_value=5.0, max_value=95.0, max_step_delta=8.0),
    "mv.damper_open_pct": MVHandlePolicy(min_value=10.0, max_value=90.0, max_step_delta=6.0),
}


def apply_mv_policy(tag: str, previous_value: float, requested_value: float) -> float:
    policy = MV_POLICIES[tag]
    bounded = min(max(float(requested_value), policy.min_value), policy.max_value)
    delta = bounded - float(previous_value)
    if delta > policy.max_step_delta:
        bounded = float(previous_value) + policy.max_step_delta
    elif delta < -policy.max_step_delta:
        bounded = float(previous_value) - policy.max_step_delta
    return min(max(bounded, policy.min_value), policy.max_value)
