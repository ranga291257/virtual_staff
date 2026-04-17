# Virtual Staff AI Operations (Standalone)

## What This Project Is

`/mnt/d/poc/virtual_staff` is a standalone Ubuntu-first project for running a
multi-agent fired-heater advisory workflow with:

- AI Process Engineer behavior (candidate generation + optimization intent),
- AI Maintenance Engineer behavior (reliability constraints + maintenance actions),
- AI Control Room Operator behavior (bounded parameter adjustment + alarm response),
- deterministic safety gating,
- Python simulator-first execution for heat/material balance evaluation,
- SQLite-backed instrument tag emulation for near-real-time state,
- fallback to deterministic calculation/control preview,
- event logging for replay and audit.

This project is advisory-only and does not perform direct OT safety-control
writes.

## Project Layout

- `virtual_staff/contracts.py`: handoff contracts, role definitions, schemas
- `virtual_staff/safety.py`: deterministic safety policy and autonomy matrix
- `virtual_staff/python_simulator.py`: Python-native simulation backend for MVP1
- `virtual_staff/tag_store.py`: SQLite tag persistence for instrument emulation
- `virtual_staff/memory_builder.py`: shared-memory builder from latest instrument tags
- `virtual_staff/instrumentation.py`: instrument tag catalog (tag, instrument ID, units, role)
- `virtual_staff/control_handles.py`: MV bounds and ramp-rate policy enforcement
- `virtual_staff/subagents.py`: process, maintenance, Control Room Operator, simulation, safety-audit subagents
- `virtual_staff/orchestrator.py`: orchestration loop, retry/timeout, operator handling, ranking, conflict handling
- `virtual_staff/event_store.py`: JSONL event store + replay helpers
- `run_virtual_staff_cycle.py`: single-cycle execution entrypoint
- `fired_heater_calcs.py`: thermal-oil fired-heater deterministic calculations
- `fired_heater_control.py`: compact control-loop preview helper
- `tests/test_virtual_staff_scenarios.py`: scenario tests
- `VIRTUAL_STAFF_OPERATIONS.md`: concise operations architecture note

Runtime-generated paths:

- `ops_events/events.jsonl`
- `mvp1_cases/<case_name>/inputs.json`
- `mvp1_cases/<case_name>/outputs.json`
- `instrument_data/heater_tags.db`
- `mvp3/dwsim_cases/<case_name>/...` (archived/deferred DWSIM assets)

## Runtime Requirements (Ubuntu)

- Python `3.10+` (tested with `python3`)
- SQLite3 (bundled with Python stdlib `sqlite3`)
- `uv` package manager for environment + installs

## Environment and Package Policy

- Always run Python from a project virtual environment.
- Use `uv`/`uv pip` for installs (do not use plain `pip` directly for project setup).
- If using CUDA/PyTorch, verify NVIDIA driver and CUDA availability before runtime tests.

Linux quick setup (recommended):

```bash
cd /mnt/d/poc/virtual_staff
python3 -m pip install --user uv
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Windows CUDA 13.0 setup (as requested):

```powershell
# IMPORTANT: CUDA 13.0 requires NVIDIA driver 600+
nvidia-smi

# Install uv one-time
C:\Users\ranga\Python314\python.exe -m pip install uv

# Create and activate venv
uv venv py3.13_venv_gpu --python C:\Users\ranga\Python314\python.exe
py3.13_venv_gpu\Scripts\Activate.ps1

# Install PyTorch CUDA 13.0 wheels
uv pip install "torch>=2.9.0" "torchvision>=0.24.0" "torchaudio>=2.9.0" --index-url https://download.pytorch.org/whl/cu130
python check_cuda.py

# Install project deps
uv pip install -r requirements.txt
```

## Quick Start

From project root:

```bash
cd /mnt/d/poc/virtual_staff
source .venv/bin/activate
python run_virtual_staff_cycle.py
```

Expected result:

- prints ranked candidate package JSON,
- writes case artifacts under `mvp1_cases/`,
- stores/reads tag samples in `instrument_data/heater_tags.db`,
- writes orchestration events under `ops_events/`.

## Run Tests

```bash
cd /mnt/d/poc/virtual_staff
source .venv/bin/activate
python -m unittest tests/test_virtual_staff_scenarios.py
```

## MVP1 Readiness Run

```bash
cd /mnt/d/poc/virtual_staff
source .venv/bin/activate
python run_mvp1_readiness.py
```

Readiness details and pass criteria are documented in `MVP1_READINESS.md`.

Current scenario coverage:

- normal cycle
- safety rejection path
- maintenance conflict path
- simulation fallback path
- retry/timeout path
- control-room operator alarm-response path
- SQLite memory builder defaults + latest-tag override paths
- MV tag write/audit loop and ramp-rate enforcement paths

## Instrumentation and Control Handles (MVP1.1)

SQLite tags model real-world instrumentation with IDs and units. Examples:

- `FI-101` -> `heater.feed_flow_kg_s`
- `TI-101` -> `heater.feed_inlet_temp_c`
- `TI-102` -> `heater.stack_temp_c`
- `TIC-101.SP` -> `heater.target_outlet_temp`
- `FV-101` -> `mv.fuel_valve_open_pct`
- `FV-102` -> `mv.air_valve_open_pct`
- `DV-101` -> `mv.damper_open_pct`

Control loop behavior:

- Agents propose candidate settings (`excess_air_fraction`, `stack_temp_c`).
- Orchestrator maps candidates to MV target tags.
- MV handles apply bounds + max-step ramp limits.
- Applied MV tag values are written to SQLite and audited in `ops_events/events.jsonl`.
- Simulator consumes PV/SP/MV state for each candidate evaluation.

## Orchestration Behavior (Cycle Summary)

1. Maintenance subagent emits active constraints and actions.
2. Process subagent emits candidate settings.
3. Control-room operator subagent adjusts candidates under operating constraints and active alarms.
4. Safety gate validates candidate bounds and autonomy tier.
5. Safety-audit subagent performs deterministic policy checks.
6. Orchestrator maps candidate values to MV target tags and applies ramp-limited writes to SQLite.
7. Simulation subagent evaluates candidate using PV/SP/MV state:
   - Python simulator-first path,
   - fallback to deterministic calc path.
8. Orchestrator applies maintenance conflict checks, ranks valid options,
   and selects action package.
9. All decisions, MV writes, and retries are logged to event store.

## Safety and Governance Boundaries

- Advisory-first operation.
- Hard deterministic checks before recommendation acceptance.
- Forbidden direct-write destinations remain blocked (BMS/SIS/DCS direct writes).
- Human-in-the-loop governance is required for real deployment execution.

## Reference Repository Role

`/home/ranga-seshadri/projects/dwsim-python-automation` is used as a
reference for deferred MVP3 DWSIM integration and not as storage for this
project's active MVP1 runtime code/artifacts.

## MVP Roadmap

- **MVP1 (active)**: Python simulator + SQLite instrument tag emulation.
- **MVP2 (planned)**: external command/control adapters (for example OpenClaw/Telegram) with governance.
- **MVP3 (deferred)**: DWSIM/pythonnet integration assets under `mvp3/`.

