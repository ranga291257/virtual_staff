# Virtual Staff AI Operations (Standalone)

## What This Project Is

`/mnt/d/poc/virtual_staff` is a standalone Ubuntu-first project for running a
multi-agent fired-heater advisory workflow with:

- AI Process Engineer behavior (candidate generation + optimization intent),
- AI Maintenance Engineer behavior (reliability constraints + maintenance actions),
- AI Control Room Operator behavior (bounded parameter adjustment + alarm response),
- deterministic safety gating,
- pythonnet-first DWSIM execution,
- fallback to script-based deterministic calculation/control preview,
- event logging for replay and audit.

This project is advisory-only and does not perform direct OT safety-control
writes.

## Project Layout

- `virtual_staff/contracts.py`: handoff contracts, role definitions, schemas
- `virtual_staff/safety.py`: deterministic safety policy and autonomy matrix
- `virtual_staff/dwsim_pythonnet_runner.py`: pythonnet-first DWSIM runner
- `virtual_staff/subagents.py`: process, maintenance, Control Room Operator, simulation, safety-audit subagents
- `virtual_staff/orchestrator.py`: orchestration loop, retry/timeout, operator handling, ranking, conflict handling
- `virtual_staff/event_store.py`: JSONL event store + replay helpers
- `run_virtual_staff_cycle.py`: single-cycle execution entrypoint
- `fired_heater_calcs.py`: thermal-oil fired-heater deterministic calculations
- `fired_heater_control.py`: compact control-loop preview helper
- `dwsim_integration_starter.py`: local case IO and DWSIM runner integration shell
- `tests/test_virtual_staff_scenarios.py`: scenario tests
- `VIRTUAL_STAFF_OPERATIONS.md`: concise operations architecture note

Runtime-generated paths:

- `ops_events/events.jsonl`
- `dwsim_cases/<case_name>/inputs.json`
- `dwsim_cases/<case_name>/outputs.json`

## Runtime Requirements (Ubuntu)

- Python `3.10+` (tested with `python3`)
- DWSIM installed on Ubuntu (common path: `/usr/local/lib/dwsim`)
- .NET runtime installed and visible to pythonnet
- pythonnet compatible environment

Suggested environment variables:

```bash
export PYTHONNET_RUNTIME=coreclr
export DOTNET_ROOT=/usr/lib/dotnet
export DWSIM_EXE=dwsim
```

Notes:

- `virtual_staff/dwsim_pythonnet_runner.py` probes Automation3 via pythonnet.
- If pythonnet path fails, execution falls back to starter-based path and then
  deterministic calc fallback behavior in subagent logic.

## Quick Start

From project root:

```bash
cd /mnt/d/poc/virtual_staff
python3 run_virtual_staff_cycle.py
```

Expected result:

- prints ranked candidate package JSON,
- writes case artifacts under `dwsim_cases/`,
- writes orchestration events under `ops_events/`.

## Run Tests

```bash
cd /mnt/d/poc/virtual_staff
python3 -m unittest tests/test_virtual_staff_scenarios.py
```

Current scenario coverage:

- normal cycle
- safety rejection path
- maintenance conflict path
- simulation fallback path
- retry/timeout path
- control-room operator alarm-response path

## Orchestration Behavior (Cycle Summary)

1. Maintenance subagent emits active constraints and actions.
2. Process subagent emits candidate settings.
3. Control-room operator subagent adjusts candidates under operating constraints and active alarms.
4. Safety gate validates candidate bounds and autonomy tier.
5. Safety-audit subagent performs deterministic policy checks.
6. Simulation subagent evaluates candidate:
   - pythonnet-first DWSIM path,
   - fallback to starter/calc path.
7. Orchestrator applies maintenance conflict checks, ranks valid options,
   and selects action package.
8. All decisions and retries are logged to event store.

## Safety and Governance Boundaries

- Advisory-first operation.
- Hard deterministic checks before recommendation acceptance.
- Forbidden direct-write destinations remain blocked (BMS/SIS/DCS direct writes).
- Human-in-the-loop governance is required for real deployment execution.

## Reference Repository Role

`/home/ranga-seshadri/projects/dwsim-python-automation` is used as a
reference for pythonnet automation patterns and not as storage for this
project's runtime code/artifacts.

