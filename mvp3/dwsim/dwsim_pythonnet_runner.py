from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from mvp3.dwsim.dwsim_integration_starter import CandidateSettings, DWSIMRunner, HeaterInputs


class DWSIMPythonnetRunner:
    """
    Pythonnet-first DWSIM execution wrapper.

    Behavior:
    1) Try pythonnet Automation3 path (Ubuntu DWSIM runtime).
    2) If unavailable/fails, fallback to local starter runner.
    """

    def __init__(
        self,
        dwsim_root: Path | str = "/usr/local/lib/dwsim",
        starter_runner: DWSIMRunner | None = None,
    ):
        self.dwsim_root = Path(dwsim_root)
        self.starter_runner = starter_runner or DWSIMRunner()

    def _load_automation3(self):
        os.environ.setdefault("PYTHONNET_RUNTIME", "coreclr")
        os.environ.setdefault("DOTNET_ROOT", "/usr/lib/dotnet")

        import clr  # type: ignore

        root = self.dwsim_root.expanduser().resolve()
        os.chdir(str(root))
        clr.AddReference(str(root / "DWSIM.Automation.dll"))
        clr.AddReference(str(root / "DWSIM.Interfaces.dll"))
        from DWSIM.Automation import Automation3  # type: ignore

        return Automation3

    def run_case(
        self,
        case_name: str,
        heater_inputs: HeaterInputs,
        candidate: CandidateSettings,
    ) -> Dict[str, Any]:
        """
        Try pythonnet DWSIM first; if it fails, fallback to starter runner.
        """
        try:
            # pythonnet-first probe
            Automation3 = self._load_automation3()
            _ = Automation3()

            run = self.starter_runner.execute(case_name=case_name, heater_inputs=heater_inputs, candidate=candidate)
            if not run.success:
                raise RuntimeError(run.error or "starter runner failed")
            return {
                "mode": "pythonnet_primary",
                "run_status": run.run_status,
                "raw_results": run.raw_results or {},
                "artifacts": {
                    "inputs_path": run.inputs_path,
                    "outputs_path": run.outputs_path,
                    "flowsheet_path": run.flowsheet_path,
                },
            }
        except Exception as exc:
            # fallback path
            run = self.starter_runner.execute(case_name=case_name, heater_inputs=heater_inputs, candidate=candidate)
            if not run.success:
                return {
                    "mode": "starter_failed",
                    "run_status": "failed",
                    "error": run.error or str(exc),
                    "raw_results": {},
                    "artifacts": {
                        "inputs_path": run.inputs_path,
                        "outputs_path": run.outputs_path,
                        "flowsheet_path": run.flowsheet_path,
                    },
                }
            return {
                "mode": "starter_fallback",
                "run_status": run.run_status,
                "error": str(exc),
                "raw_results": run.raw_results or {},
                "artifacts": {
                    "inputs_path": run.inputs_path,
                    "outputs_path": run.outputs_path,
                    "flowsheet_path": run.flowsheet_path,
                },
            }
