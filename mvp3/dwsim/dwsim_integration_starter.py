"""
DWSIM integration starter for a thermal-oil fired-heater hybrid package.

This starter is aligned to:
- process side: thermal oil sensible heating (liquid-only assumption),
- combustion side: methane + air with excess-air control,
- script support: stack-loss-based efficiency and flue-gas calculations.

It keeps file exchange simple and can later be upgraded to COM/.NET automation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional
import json
import os
import shutil
import time
from fired_heater_calcs import CombustionBasis, ProcessBasis, solve_fired_heater


# Ubuntu-first defaults:
# - DWSIM executable can be provided via DWSIM_EXE
# - fallback to "dwsim" (must be available in PATH)
DEFAULT_DWSIM_EXE = Path(os.getenv("DWSIM_EXE", "dwsim"))
DEFAULT_WORKDIR = Path(__file__).resolve().parent.parent / "dwsim_cases"


@dataclass
class HeaterInputs:
    heater_id: str
    feed_flow_kg_s: float
    feed_inlet_temp_c: float
    target_outlet_temp: float
    cp_kj_kg_k: float = 2.5
    density_kg_m3: float = 800.0
    process_pressure_barg: float = 10.0
    tube_dp_bar: float = 1.5
    extra: Optional[Dict[str, Any]] = None


@dataclass
class CandidateSettings:
    excess_air_fraction: float = 0.10
    stack_temp_c: float = 250.0
    ambient_temp_c: float = 25.0
    methane_lhv_kj_kg: float = 50_000.0
    cp_flue_kj_kg_k: float = 1.10
    notes: Optional[str] = None


@dataclass
class DWSIMRunResult:
    success: bool
    run_status: str
    run_seconds: float
    flowsheet_path: str
    inputs_path: str
    outputs_path: str
    outlet_temp_pred_c: Optional[float] = None
    absorbed_duty_kw: Optional[float] = None
    fired_duty_kw: Optional[float] = None
    methane_kg_s: Optional[float] = None
    air_kg_s: Optional[float] = None
    efficiency_est: Optional[float] = None
    raw_results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DWSIMRunner:
    def __init__(self, dwsim_exe: Path = DEFAULT_DWSIM_EXE, workdir: Path = DEFAULT_WORKDIR):
        self.dwsim_exe = Path(dwsim_exe)
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)

    def validate_installation(self) -> None:
        exe_str = str(self.dwsim_exe)
        if self.dwsim_exe.is_absolute():
            if not self.dwsim_exe.exists():
                raise FileNotFoundError(f"DWSIM executable not found: {self.dwsim_exe}")
            return

        if shutil.which(exe_str) is None:
            raise FileNotFoundError(
                f"DWSIM executable not found in PATH: {exe_str}. "
                "Set DWSIM_EXE to an absolute path or install dwsim in PATH."
            )

    def build_case_payload(self, heater_inputs: HeaterInputs, candidate: CandidateSettings) -> Dict[str, Any]:
        return {
            "heater_inputs": asdict(heater_inputs),
            "candidate_settings": asdict(candidate),
        }

    def write_case_files(self, case_name: str, payload: Dict[str, Any]) -> Dict[str, Path]:
        case_dir = self.workdir / case_name
        case_dir.mkdir(parents=True, exist_ok=True)

        inputs_path = case_dir / "inputs.json"
        outputs_path = case_dir / "outputs.json"
        flowsheet_path = case_dir / "thermal_oil_fired_heater.dwxmz"  # placeholder

        inputs_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        if not flowsheet_path.exists():
            flowsheet_path.write_text(
                "Placeholder flowsheet path file. Replace with copied/calibrated DWSIM flowsheet.",
                encoding="utf-8",
            )

        return {
            "case_dir": case_dir,
            "inputs_path": inputs_path,
            "outputs_path": outputs_path,
            "flowsheet_path": flowsheet_path,
        }

    def run_dwsim_case(self, flowsheet_path: Path, inputs_path: Path, outputs_path: Path) -> Dict[str, Any]:
        """
        Starter implementation.

        Placeholder implementation:
        - reads prepared payload
        - runs thermal-oil/combustion calculations via script support
        - writes outputs as if they were returned by a DWSIM+script workflow
        """
        _ = flowsheet_path
        payload = json.loads(inputs_path.read_text(encoding="utf-8"))
        h = payload["heater_inputs"]
        c = payload["candidate_settings"]

        pb = ProcessBasis(
            mass_flow_kg_s=h["feed_flow_kg_s"],
            inlet_temp_c=h["feed_inlet_temp_c"],
            outlet_temp_c=h["target_outlet_temp"],
            cp_kj_kg_k=h["cp_kj_kg_k"],
            density_kg_m3=h["density_kg_m3"],
        )
        cb = CombustionBasis(
            excess_air_fraction=c["excess_air_fraction"],
            methane_lhv_kj_kg=c["methane_lhv_kj_kg"],
            stack_temp_c=c["stack_temp_c"],
            ambient_temp_c=c["ambient_temp_c"],
            cp_flue_kj_kg_k=c["cp_flue_kj_kg_k"],
        )

        solved = solve_fired_heater(pb, cb)
        simulated_results = {
            "outlet_temp_pred_c": pb.outlet_temp_c,
            "absorbed_duty_kw": solved.absorbed_duty_kw,
            "fired_duty_kw": solved.fired_duty_kw,
            "methane_kg_s": solved.methane_kg_s,
            "air_kg_s": solved.air_kg_s,
            "efficiency_est": solved.efficiency,
            "flue_wet_mole_frac": solved.flue_wet_mole_frac,
            "flue_dry_mole_frac": solved.flue_dry_mole_frac,
            "stack_loss_kw": solved.stack_loss_kw,
        }
        outputs_path.write_text(json.dumps(simulated_results, indent=2), encoding="utf-8")
        return simulated_results

    def execute(self, case_name: str, heater_inputs: HeaterInputs, candidate: CandidateSettings) -> DWSIMRunResult:
        self.validate_installation()
        payload = self.build_case_payload(heater_inputs, candidate)
        paths = self.write_case_files(case_name, payload)

        t0 = time.time()
        try:
            results = self.run_dwsim_case(
                flowsheet_path=paths["flowsheet_path"],
                inputs_path=paths["inputs_path"],
                outputs_path=paths["outputs_path"],
            )
            elapsed = time.time() - t0
            return DWSIMRunResult(
                success=True,
                run_status="success",
                run_seconds=elapsed,
                flowsheet_path=str(paths["flowsheet_path"]),
                inputs_path=str(paths["inputs_path"]),
                outputs_path=str(paths["outputs_path"]),
                outlet_temp_pred_c=results.get("outlet_temp_pred_c"),
                absorbed_duty_kw=results.get("absorbed_duty_kw"),
                fired_duty_kw=results.get("fired_duty_kw"),
                methane_kg_s=results.get("methane_kg_s"),
                air_kg_s=results.get("air_kg_s"),
                efficiency_est=results.get("efficiency_est"),
                raw_results=results,
            )
        except Exception as exc:
            elapsed = time.time() - t0
            return DWSIMRunResult(
                success=False,
                run_status="failed",
                run_seconds=elapsed,
                flowsheet_path=str(paths["flowsheet_path"]),
                inputs_path=str(paths["inputs_path"]),
                outputs_path=str(paths["outputs_path"]),
                error=str(exc),
            )


if __name__ == "__main__":
    runner = DWSIMRunner()

    heater_inputs = HeaterInputs(
        heater_id="FH-101",
        feed_flow_kg_s=100.0,
        feed_inlet_temp_c=260.0,
        target_outlet_temp=300.0,
        cp_kj_kg_k=2.5,
        density_kg_m3=800.0,
        process_pressure_barg=10.0,
        tube_dp_bar=1.5,
    )

    candidate = CandidateSettings(
        excess_air_fraction=0.10,
        stack_temp_c=250.0,
        ambient_temp_c=25.0,
        methane_lhv_kj_kg=50_000.0,
        cp_flue_kj_kg_k=1.10,
        notes="Base thermal-oil fired-heater case with O2-trim-ready settings.",
    )

    try:
        result = runner.execute(case_name="fh101_case_001", heater_inputs=heater_inputs, candidate=candidate)
        print(json.dumps(asdict(result), indent=2))
    except FileNotFoundError:
        # Graceful behavior for environments where DWSIM is not installed at the default Windows path.
        payload = runner.build_case_payload(heater_inputs=heater_inputs, candidate=candidate)
        paths = runner.write_case_files(case_name="fh101_case_001", payload=payload)
        preview = runner.run_dwsim_case(
            flowsheet_path=paths["flowsheet_path"],
            inputs_path=paths["inputs_path"],
            outputs_path=paths["outputs_path"],
        )
        print(json.dumps({"note": "DWSIM executable not found, generated script-based preview.", "preview": preview}, indent=2))
