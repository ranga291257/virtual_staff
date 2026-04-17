# Context for Cursor Session (Virtual Staff)

## Mission

Run a standalone multi-agent fired-heater advisory system with deterministic
safety and traceable orchestration cycles.

## Non-Goals

- No direct autonomous writes to BMS/SIS/DCS.
- No cloud-only dependency assumption.
- No use of reference automation repo as artifact storage.

## Key Runtime Facts

- Project home: `/mnt/d/poc/virtual_staff`
- DWSIM automation reference repo:
  `/home/ranga-seshadri/projects/dwsim-python-automation`
- SQLite tag DB path (MVP1 active): `instrument_data/heater_tags.db`

## Important Files

- `virtual_staff/orchestrator.py`
  - Core cycle controller, handoff retry/timeout, ranking, conflict rejection, operator handling
- `virtual_staff/subagents.py`
  - Process optimization, maintenance, control room operator, simulation, safety audit behaviors
- `virtual_staff/python_simulator.py`
  - Python-native dynamic simulator for candidate evaluation
- `virtual_staff/tag_store.py`
  - SQLite instrument tag storage and latest value reads
- `virtual_staff/memory_builder.py`
  - Shared memory build from current instrument tags
- `virtual_staff/instrumentation.py`
  - Tag catalog with instrument IDs, units, and signal roles (PV/SP/MV)
- `virtual_staff/control_handles.py`
  - MV bounds and ramp-rate policy enforcement
- `virtual_staff/safety.py`
  - Deterministic policy, autonomy tiers, validation bounds
- `virtual_staff/event_store.py`
  - JSONL event append and replay helpers
- `fired_heater_calcs.py`
  - Deterministic fired-heater balance and combustion outputs
- `fired_heater_control.py`
  - Closed-loop preview (used as compact control sanity trace)
- `tests/test_virtual_staff_scenarios.py`
  - Regression scenarios for normal/reject/conflict/fallback/retry-timeout/operator-alarm/sqlite-memory/MV-handles
- `mvp3/dwsim/`
  - Deferred DWSIM/pythonnet integration assets for MVP3

## Core Data Flow

1. Build shared memory (`default_memory` or runtime state source).
2. Maintenance subagent returns constraints.
3. Process subagent emits candidate list.
4. Control room operator subagent adjusts candidate under active alarms and constraints.
5. Safety gate + safety audit validate each candidate.
6. Orchestrator maps candidates to MV tags and writes ramp-limited commands to SQLite.
7. Simulation subagent evaluates candidate using PV/SP/MV state:
   - Python simulator-first path,
   - fallback to deterministic calculation path.
8. Orchestrator applies maintenance conflict checks, ranks, selects.
9. Event store logs all key events (including MV writes) for replay.

## Runtime Output Paths

- `ops_events/events.jsonl`
- `mvp1_cases/<case>/inputs.json`
- `mvp1_cases/<case>/outputs.json`
- `instrument_data/heater_tags.db`
- `mvp3/dwsim_cases/<case>/...` (deferred MVP3 assets)

## Environment Setup Hints

MVP1 setup (Python + SQLite):

- ensure Python `3.10+` is available
- SQLite is available via Python stdlib (`sqlite3`)
- create and use a virtual environment for all Python runs
- use `uv`/`uv pip` for dependency install workflows
- use `check_cuda.py` before GPU-dependent workloads

## First Commands in New Cursor Session

```bash
cd /mnt/d/poc/virtual_staff
source .venv/bin/activate
python -m unittest tests/test_virtual_staff_scenarios.py
python run_virtual_staff_cycle.py
```

## Known Decisions

- Standalone sibling project (no wrappers).
- All virtual-staff related implementation moved from old repo.
- Reference automation repo remains read/reference only.
- MVP1 uses Python simulator + SQLite instrumentation.
- DWSIM materials moved under `mvp3/` for deferred MVP3 activation.

