# MVP1 Readiness (Python Simulator + SQLite)

## Scope

MVP1 is complete when the runtime demonstrates:

- SQLite-backed instrument state ingestion,
- bounded MV command writes with ramp-rate enforcement,
- deterministic safety + audit traceability,
- stable advisory outputs for normal/alarm/conflict scenarios.

## Required Runtime Artifacts

- `instrument_data/heater_tags.db`
- `mvp1_cases/<case>/inputs.json`
- `mvp1_cases/<case>/outputs.json`
- `ops_events/events.jsonl`
- `ops_events/mvp1_readiness_summary.json`

## Verification Commands

```bash
cd /mnt/d/poc/virtual_staff
source .venv/bin/activate
python -m unittest tests/test_virtual_staff_scenarios.py
python run_mvp1_readiness.py
```

## Pass Criteria

- All tests pass.
- Readiness runner completes 3 scenarios:
  - `mvp1_normal`
  - `mvp1_alarm`
  - `mvp1_conflict`
- `ops_events/mvp1_readiness_summary.json` is generated.
- Event log contains MV write records:
  - `event_type = "mv_tag_write"`
- Summary shows each case has:
  - non-empty ranking or explicit rejected results,
  - runtime mode present (`python_simulator` or `calc_fallback`).

## Operational Notes

- SQLite is seeded automatically with default tags on first run.
- Execute all Python commands from the project virtual environment.
- Install dependencies with `uv pip` (not plain `pip`) for project setup consistency.
- Agent recommendations are mapped to MV tags:
  - `mv.fuel_valve_open_pct`
  - `mv.air_valve_open_pct`
  - `mv.damper_open_pct`
- MV policies enforce both bounds and per-step ramp limits.
