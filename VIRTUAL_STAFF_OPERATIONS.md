# Virtual Staff AI Operations

## Purpose

This document defines the pilot-local, high-autonomy virtual staff runtime for:

- AI Process Engineer
- AI Maintenance Engineer
- AI Control Room Operator
- Orchestrator + specialist subagents

It is aligned to the fired-heater reference case and advisory-first governance.

## Runtime Components

- `virtual_staff/contracts.py`: role contracts, handoff models, schema definitions
- `virtual_staff/safety.py`: deterministic safety policy, autonomy envelope
- `virtual_staff/subagents.py`: process optimization, maintenance, Control Room Operator, simulation, safety-audit subagents
- `virtual_staff/python_simulator.py`: Python-native simulation backend for MVP1
- `virtual_staff/tag_store.py`: SQLite-backed instrument tag store
- `virtual_staff/memory_builder.py`: shared-memory builder from latest instrument values
- `virtual_staff/instrumentation.py`: instrument catalog with IDs/units/roles
- `virtual_staff/control_handles.py`: MV policies for bounds and ramp limits
- `virtual_staff/orchestrator.py`: cycle scheduling logic, handoff/retry, ranking, and publication package
- `virtual_staff/event_store.py`: JSONL event log and replay support
- `run_virtual_staff_cycle.py`: single-cycle execution entrypoint
- `tests/test_virtual_staff_scenarios.py`: normal/rejection/conflict/fallback/retry-timeout/operator-alarm/sqlite-memory scenario tests

Deferred modules:

- `mvp3/dwsim/`: DWSIM/pythonnet integration assets reserved for MVP3

## Autonomy Matrix

Even with high-autonomy mode, deterministic constraints are enforced before publication:

- `read_only_analysis`: auto
- `candidate_evaluation`: auto with safety gate
- `recommendation_publish`: guarded auto
- `work_order_prepare`: guarded auto
- `ot_write_request`: human acknowledgment required

Forbidden destinations are hard-blocked:

- `bms_write`
- `sis_write`
- `dcs_direct_write`

## Handoff Protocol

Every subagent handoff includes:

- `request_id` and optional `parent_request_id`
- `role`
- `intent` (action type, risk class, confidence, evidence)
- deterministic `context` package
- `timeout_seconds` and `retry_limit`

Each response must include:

- success/failure status
- output payload
- artifact paths (if any)
- evidence and errors

## Orchestration Sequence

1. Maintenance subagent emits active constraints and maintenance actions.
2. Process optimization subagent generates candidate settings.
3. Control Room Operator subagent applies bounded adjustments using active alarms and operating constraints.
4. Deterministic safety gate validates each candidate.
5. Safety audit subagent performs policy-level checks.
6. Orchestrator maps candidate values to MV tag commands and applies ramp-limited writes to SQLite.
7. Simulation subagent runs Python simulator with PV/SP/MV state; falls back to deterministic calc if needed.
8. Orchestrator ranks feasible candidates and emits selected action package.
9. Event store logs handoffs, MV writes, rejections, and cycle completion for replay.

## MVP Boundaries

- **MVP1 (active)**: Python simulator + SQLite instrument emulation + advisory orchestration.
- **MVP2 (planned)**: operator-facing integrations and governed command workflows.
- **MVP3 (deferred)**: DWSIM/pythonnet-backed simulation stack under `mvp3/`.

## Local Pilot Boundaries

- Local-only runtime and local file-based event storage
- Recommendation/action package output only
- No direct OT safety-control writes
- Full traceability of each cycle and rejection rationale
