from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Dict

from fired_heater_calcs import CombustionBasis, ProcessBasis, solve_fired_heater


class PythonHeaterSimulator:
    def __init__(self, workdir: Path | str = "mvp1_cases"):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)

    def execute(self, case_name: str, heater_inputs: Dict[str, float], candidate: Dict[str, float]) -> Dict[str, Any]:
        fuel_valve_open_pct = float(heater_inputs.get("fuel_valve_open_pct", 52.0))
        air_valve_open_pct = float(heater_inputs.get("air_valve_open_pct", 48.0))
        damper_open_pct = float(heater_inputs.get("damper_open_pct", 45.0))

        # MV handles softly bias candidate values to mimic instrumented control action.
        adjusted_excess_air = float(candidate["excess_air_fraction"]) * (0.85 + (air_valve_open_pct / 320.0))
        adjusted_excess_air = min(max(adjusted_excess_air, 0.02), 0.30)
        adjusted_stack_temp = float(candidate["stack_temp_c"]) + (fuel_valve_open_pct - 50.0) * 0.25
        adjusted_stack_temp -= (damper_open_pct - 45.0) * 0.35

        pb = ProcessBasis(
            mass_flow_kg_s=float(heater_inputs["feed_flow_kg_s"]),
            inlet_temp_c=float(heater_inputs["feed_inlet_temp_c"]),
            outlet_temp_c=float(heater_inputs["target_outlet_temp"]),
            cp_kj_kg_k=float(heater_inputs.get("cp_kj_kg_k", 2.5)),
            density_kg_m3=float(heater_inputs.get("density_kg_m3", 800.0)),
        )
        cb = CombustionBasis(
            excess_air_fraction=adjusted_excess_air,
            stack_temp_c=adjusted_stack_temp,
            ambient_temp_c=float(candidate.get("ambient_temp_c", 25.0)),
            methane_lhv_kj_kg=float(candidate.get("methane_lhv_kj_kg", 50_000.0)),
            cp_flue_kj_kg_k=float(candidate.get("cp_flue_kj_kg_k", 1.10)),
        )
        solved = solve_fired_heater(pb, cb)
        raw_results = asdict(solved)
        raw_results["outlet_temp_pred_c"] = pb.outlet_temp_c
        raw_results["candidate"] = dict(candidate)
        raw_results["mv_snapshot"] = {
            "fuel_valve_open_pct": fuel_valve_open_pct,
            "air_valve_open_pct": air_valve_open_pct,
            "damper_open_pct": damper_open_pct,
        }
        raw_results["adjusted_candidate"] = {
            "excess_air_fraction": adjusted_excess_air,
            "stack_temp_c": adjusted_stack_temp,
        }

        case_dir = self.workdir / case_name
        case_dir.mkdir(parents=True, exist_ok=True)
        inputs_path = case_dir / "inputs.json"
        outputs_path = case_dir / "outputs.json"
        inputs_path.write_text(
            json.dumps({"heater_state": heater_inputs, "candidate": candidate}, indent=2),
            encoding="utf-8",
        )
        outputs_path.write_text(json.dumps(raw_results, indent=2), encoding="utf-8")

        return {
            "mode": "python_simulator",
            "run_status": "success",
            "raw_results": raw_results,
            "artifacts": {
                "inputs_path": str(inputs_path),
                "outputs_path": str(outputs_path),
            },
        }
