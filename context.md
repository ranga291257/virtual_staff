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
- Typical Ubuntu DWSIM install root: `/usr/local/lib/dwsim`

## Important Files

- `virtual_staff/orchestrator.py`
  - Core cycle controller, handoff retry/timeout, ranking, conflict rejection
- `virtual_staff/subagents.py`
  - Process optimization, maintenance, simulation, safety audit behaviors
- `virtual_staff/dwsim_pythonnet_runner.py`
  - pythonnet Automation3 probe and DWSIM run path selection
- `virtual_staff/safety.py`
  - Deterministic policy, autonomy tiers, validation bounds
- `virtual_staff/event_store.py`
  - JSONL event append and replay helpers
- `fired_heater_calcs.py`
  - Deterministic fired-heater balance and combustion outputs
- `fired_heater_control.py`
  - Closed-loop preview (used as compact control sanity trace)
- `tests/test_virtual_staff_scenarios.py`
  - Regression scenarios for normal/reject/conflict/fallback/retry-timeout

## Core Data Flow

1. Build shared memory (`default_memory` or runtime state source).
2. Maintenance subagent returns constraints.
3. Process subagent emits candidate list.
4. Safety gate + safety audit validate each candidate.
5. Simulation subagent evaluates candidate:
   - pythonnet-first path,
   - fallback to deterministic calculation path.
6. Orchestrator applies maintenance conflict checks, ranks, selects.
7. Event store logs all key events for replay.

## Runtime Output Paths

- `ops_events/events.jsonl`
- `dwsim_cases/<case>/inputs.json`
- `dwsim_cases/<case>/outputs.json`

## Environment Setup Hints

Use when pythonnet path is needed:

```bash
export PYTHONNET_RUNTIME=coreclr
export DOTNET_ROOT=/usr/lib/dotnet
export DWSIM_EXE=dwsim
```

If pythonnet load fails:

- verify DWSIM files under `/usr/local/lib/dwsim`
- verify `DOTNET_ROOT`
- run with fallback path and inspect `runtime_mode` in outputs

## First Commands in New Cursor Session

```bash
cd /mnt/d/poc/virtual_staff
python3 -m unittest tests/test_virtual_staff_scenarios.py
python3 run_virtual_staff_cycle.py
```

## Known Decisions

- Standalone sibling project (no wrappers).
- All virtual-staff related implementation moved from old repo.
- Reference automation repo remains read/reference only.

