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
- `virtual_staff/dwsim_pythonnet_runner.py`: pythonnet-first DWSIM Automation3 runner with starter fallback
- `virtual_staff/orchestrator.py`: cycle scheduling logic, handoff/retry, ranking, and publication package
- `virtual_staff/event_store.py`: JSONL event log and replay support
- `run_virtual_staff_cycle.py`: single-cycle execution entrypoint
- `tests/test_virtual_staff_scenarios.py`: normal/rejection/conflict/fallback/retry-timeout/operator-alarm scenario tests

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
6. Simulation subagent runs pythonnet-first DWSIM; falls back to starter and then deterministic calc if needed.
7. Orchestrator ranks feasible candidates and emits selected action package.
8. Event store logs handoffs, rejections, and cycle completion for replay.

## Local Pilot Boundaries

- Local-only runtime and local file-based event storage
- Recommendation/action package output only
- No direct OT safety-control writes
- Full traceability of each cycle and rejection rationale
