# Virtual Staff AI for Fired Heaters

## Executive Brief

`virtual_staff` delivers a practical AI operations advisory system for fired
heaters by combining Process, Maintenance, and Control Room Operator behaviors
into one governed orchestration runtime.

It is built for industrial use: deterministic safety checks, traceable
decisions, simulation-backed evaluation, and resilient fallback paths.

## What Has Been Delivered

- Multi-agent orchestration for process, maintenance, and operator roles
- Control Room Operator logic for alarm-aware, bounded parameter adjustment
- Deterministic safety gate and policy validation before recommendation publish
- Python simulator-first evaluation with deterministic fallback continuity
- Conflict-aware ranking and action package selection
- Replayable event logging for audit and governance
- Regression coverage for normal, reject, conflict, fallback, timeout, operator-alarm, sqlite-memory, and MV-handle scenarios

## Strategic Value

- **Safer optimization**: recommendations remain inside explicit policy limits
- **Higher reliability**: maintenance constraints are part of optimization flow
- **Faster decisions**: ranked action packages reduce response time
- **Operational resilience**: advisory continuity during simulation/runtime issues
- **Governance-ready**: full traceability of handoffs, rejections, and selections

## Safety and Control Posture

- Advisory-first architecture (no direct autonomous BMS/SIS/DCS writes)
- Human governance preserved for real deployment execution
- Deterministic checks enforce confidence, parameter bounds, and destination restrictions

## Why This Is Different

This is not a generic AI assistant.  
It is a role-based operational advisory system aligned to control-room and
plant governance realities.

## Recommended Next Steps

1. Add operator approval workflow and acknowledgment tracking
2. Define site-specific alarm taxonomy and response templates
3. Add KPI dashboard for recommendation quality/adoption
4. Start controlled pilot with historian/CMMS context integration
5. Activate DWSIM/pythonnet path as MVP3 once calibration scope is approved

