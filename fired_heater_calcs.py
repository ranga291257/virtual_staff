from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Dict


MW = {
    "CH4": 16.043,
    "O2": 31.999,
    "N2": 28.014,
    "CO2": 44.009,
    "H2O": 18.015,
}

AIR_O2 = 0.21
AIR_N2 = 0.79


@dataclass
class ProcessBasis:
    mass_flow_kg_s: float = 100.0
    inlet_temp_c: float = 260.0
    outlet_temp_c: float = 300.0
    cp_kj_kg_k: float = 2.5
    density_kg_m3: float = 800.0


@dataclass
class CombustionBasis:
    excess_air_fraction: float = 0.10
    methane_lhv_kj_kg: float = 50_000.0
    stack_temp_c: float = 250.0
    ambient_temp_c: float = 25.0
    cp_flue_kj_kg_k: float = 1.10


@dataclass
class FiredHeaterResult:
    absorbed_duty_kw: float
    fired_duty_kw: float
    methane_kg_s: float
    methane_kmol_s: float
    air_kg_s: float
    air_kmol_s: float
    flue_wet_kmol_s: Dict[str, float]
    flue_wet_mole_frac: Dict[str, float]
    flue_dry_mole_frac: Dict[str, float]
    flue_total_kg_s: float
    stack_loss_kw: float
    efficiency: float


def _validate_positive(value: float, name: str) -> None:
    if not isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be a positive finite number.")


def absorbed_duty_kw(pb: ProcessBasis) -> float:
    _validate_positive(pb.mass_flow_kg_s, "mass_flow_kg_s")
    _validate_positive(pb.cp_kj_kg_k, "cp_kj_kg_k")
    delta_t = pb.outlet_temp_c - pb.inlet_temp_c
    if delta_t <= 0.0:
        raise ValueError("outlet_temp_c must be greater than inlet_temp_c for heating.")
    return pb.mass_flow_kg_s * pb.cp_kj_kg_k * delta_t


def _combustion_from_methane(methane_kmol_s: float, excess_air_fraction: float) -> Dict[str, float]:
    stoich_o2 = 2.0 * methane_kmol_s
    stoich_air = stoich_o2 / AIR_O2
    air_kmol_s = stoich_air * (1.0 + excess_air_fraction)
    o2_in = air_kmol_s * AIR_O2
    n2_in = air_kmol_s * AIR_N2

    co2 = methane_kmol_s
    h2o = 2.0 * methane_kmol_s
    o2_excess = max(o2_in - stoich_o2, 0.0)

    return {
        "air_kmol_s": air_kmol_s,
        "CO2": co2,
        "H2O": h2o,
        "O2": o2_excess,
        "N2": n2_in,
    }


def solve_fired_heater(pb: ProcessBasis, cb: CombustionBasis) -> FiredHeaterResult:
    _validate_positive(cb.methane_lhv_kj_kg, "methane_lhv_kj_kg")
    _validate_positive(cb.cp_flue_kj_kg_k, "cp_flue_kj_kg_k")

    q_abs = absorbed_duty_kw(pb)

    # Initial screening estimate around typical thermal-oil heater efficiency.
    q_fired = q_abs / 0.88

    for _ in range(8):
        methane_kg_s = q_fired / cb.methane_lhv_kj_kg
        methane_kmol_s = methane_kg_s / MW["CH4"]
        comb = _combustion_from_methane(methane_kmol_s, cb.excess_air_fraction)
        flue_total_kg_s = (
            comb["CO2"] * MW["CO2"]
            + comb["H2O"] * MW["H2O"]
            + comb["O2"] * MW["O2"]
            + comb["N2"] * MW["N2"]
        )
        stack_loss_kw = flue_total_kg_s * cb.cp_flue_kj_kg_k * (cb.stack_temp_c - cb.ambient_temp_c)
        q_fired = q_abs + stack_loss_kw

    methane_kg_s = q_fired / cb.methane_lhv_kj_kg
    methane_kmol_s = methane_kg_s / MW["CH4"]
    comb = _combustion_from_methane(methane_kmol_s, cb.excess_air_fraction)
    flue_wet = {
        "CO2": comb["CO2"],
        "H2O": comb["H2O"],
        "O2": comb["O2"],
        "N2": comb["N2"],
    }
    wet_total = sum(flue_wet.values())
    dry_total = wet_total - flue_wet["H2O"]
    flue_wet_frac = {k: v / wet_total for k, v in flue_wet.items()}
    flue_dry_frac = {
        "CO2": flue_wet["CO2"] / dry_total,
        "O2": flue_wet["O2"] / dry_total,
        "N2": flue_wet["N2"] / dry_total,
    }
    air_kg_s = comb["air_kmol_s"] * (AIR_O2 * MW["O2"] + AIR_N2 * MW["N2"])
    flue_total_kg_s = (
        flue_wet["CO2"] * MW["CO2"]
        + flue_wet["H2O"] * MW["H2O"]
        + flue_wet["O2"] * MW["O2"]
        + flue_wet["N2"] * MW["N2"]
    )
    stack_loss_kw = flue_total_kg_s * cb.cp_flue_kj_kg_k * (cb.stack_temp_c - cb.ambient_temp_c)
    efficiency = q_abs / q_fired

    return FiredHeaterResult(
        absorbed_duty_kw=q_abs,
        fired_duty_kw=q_fired,
        methane_kg_s=methane_kg_s,
        methane_kmol_s=methane_kmol_s,
        air_kg_s=air_kg_s,
        air_kmol_s=comb["air_kmol_s"],
        flue_wet_kmol_s=flue_wet,
        flue_wet_mole_frac=flue_wet_frac,
        flue_dry_mole_frac=flue_dry_frac,
        flue_total_kg_s=flue_total_kg_s,
        stack_loss_kw=stack_loss_kw,
        efficiency=efficiency,
    )


if __name__ == "__main__":
    res = solve_fired_heater(ProcessBasis(), CombustionBasis())
    import json

    print(json.dumps(asdict(res), indent=2))
