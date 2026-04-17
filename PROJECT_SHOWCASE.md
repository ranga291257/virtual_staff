# Virtual Staff AI for Fired Heaters

## Turning Operations Expertise into a Scalable AI Team

`virtual_staff` is a standalone, production-oriented advisory system that brings
the roles of Process Engineer, Maintenance Engineer, and Control Room Operator
into a coordinated AI runtime for fired-heater operations.

It is designed for industrial reality: safety first, deterministic guardrails,
traceable decisions, and local execution readiness.

---

## What We Built

We implemented a multi-agent orchestration platform that can:

- generate process optimization candidates,
- enforce maintenance reliability constraints,
- adapt recommendations through control-room-style alarm response behavior,
- run simulation-first evaluation with deterministic fallback resilience,
- rank and publish best action packages with full traceability.

This is not a generic chatbot workflow. It is a structured operational advisory
engine aligned to plant workflows and governance expectations.

---

## Core Differentiators

### 1) Multi-Role AI Collaboration by Design

The system mirrors how real teams operate:

- **Process role** proposes optimized settings.
- **Maintenance role** applies asset health constraints.
- **Control Room Operator role** performs bounded, alarm-aware adjustments.
- **Safety and simulation roles** validate before selection.
- **Orchestrator** resolves, ranks, and packages outcomes.

### 2) Deterministic Safety Architecture

Safety is built into the workflow, not added after the fact:

- deterministic safety gate,
- explicit autonomy tiers,
- policy-bound parameter checks,
- forbidden destination blocking (`BMS/SIS/DCS` direct writes).

### 3) Simulation-First, Always-Operational Runtime

Evaluation prioritizes high-fidelity simulation paths while keeping continuity:

1. Python simulator path (MVP1 active),
2. deterministic calculation fallback,
3. DWSIM/pythonnet path (deferred to MVP3).

This ensures advisory continuity even during integration/runtime disruptions.

### 4) Auditability and Governance Readiness

Every handoff and decision is recorded in event logs for replay and review:

- cycle start/end,
- subagent handoff success/retry/timeout,
- MV tag write decisions and applied ramp-limited values,
- candidate rejection reasons,
- ranked and selected outputs.

---

## Business Value Delivered

- **Faster decision support** for heater operating windows.
- **Safer recommendations** through deterministic policy enforcement.
- **Improved reliability posture** via maintenance-aware optimization.
- **Operational resilience** from layered fallback execution modes.
- **Transparent governance** with replayable event evidence.

---

## Delivered Scope in This Project

- Standalone project architecture under `virtual_staff`
- Contract-driven handoff models and role definitions
- Orchestrator with retry/timeout, conflict handling, and ranking
- Control Room Operator subagent integration (alarm-constrained adjustments)
- Safety audit and deterministic policy validation
- Python simulator integration with SQLite-backed instrument emulation
- Instrumentation tag catalog with valve/damper handles and ramp-limited command application
- Scenario-based regression tests (normal/reject/conflict/fallback/retry/operator alarm/sqlite-memory)
- Updated operations and context documentation for consistency

---

## Why This Matters

Most AI demos stop at “can generate suggestions.”  
This project demonstrates “can operate within industrial constraints.”

It is a practical bridge between advanced AI orchestration and real-world plant
governance requirements, setting the foundation for controlled pilot deployment.

---

## Next-Phase Opportunities

- Add alarm taxonomy and response playbooks by equipment class
- Introduce approval workflows and operator acknowledgment UI
- Add KPI dashboards for recommendation quality and adoption
- Expand from fired heaters to adjacent thermal and utility assets
- Integrate site historian/CMMS data feeds for richer context

