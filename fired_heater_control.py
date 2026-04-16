from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List

from fired_heater_calcs import CombustionBasis, ProcessBasis, solve_fired_heater


@dataclass
class ControlTuning:
    kp_temp: float = 0.02
    ki_temp: float = 0.001
    kp_o2_trim: float = 0.15
    target_o2_dry: float = 0.021  # ~2.1% dry basis for 10% excess air
    max_trim_frac: float = 0.15


@dataclass
class SimulationPoint:
    step: int
    process_inlet_temp_c: float
    process_outlet_target_c: float
    methane_kg_s: float
    air_kg_s: float
    o2_dry: float
    efficiency: float


def run_closed_loop_demo(
    steps: int = 20,
    disturbance_step: int = 8,
    inlet_temp_drop_c: float = 10.0,
) -> List[Dict[str, float]]:
    pb = ProcessBasis()
    cb = CombustionBasis()
    tuning = ControlTuning()

    base = solve_fired_heater(pb, cb)
    fuel_bias = base.methane_kg_s
    integ = 0.0
    ratio_air_to_fuel = base.air_kg_s / base.methane_kg_s
    o2_trim = 0.0

    records: List[SimulationPoint] = []

    for step in range(steps):
        if step == disturbance_step:
            pb.inlet_temp_c -= inlet_temp_drop_c

        result = solve_fired_heater(pb, cb)

        # Temperature loop (simplified): fuel bias toward required fuel.
        temp_error = result.methane_kg_s - fuel_bias
        integ += temp_error
        fuel_bias += tuning.kp_temp * temp_error + tuning.ki_temp * integ
        methane_cmd = max(fuel_bias, 0.01)

        # Air-ratio control + O2 trim.
        o2_dry = result.flue_dry_mole_frac["O2"]
        o2_err = tuning.target_o2_dry - o2_dry
        o2_trim += tuning.kp_o2_trim * o2_err
        o2_trim = max(min(o2_trim, tuning.max_trim_frac), -tuning.max_trim_frac)
        air_cmd = methane_cmd * ratio_air_to_fuel * (1.0 + o2_trim)

        records.append(
            SimulationPoint(
                step=step,
                process_inlet_temp_c=pb.inlet_temp_c,
                process_outlet_target_c=pb.outlet_temp_c,
                methane_kg_s=methane_cmd,
                air_kg_s=air_cmd,
                o2_dry=o2_dry,
                efficiency=result.efficiency,
            )
        )

    return [asdict(r) for r in records]


if __name__ == "__main__":
    import json

    out = run_closed_loop_demo()
    print(json.dumps(out, indent=2))
