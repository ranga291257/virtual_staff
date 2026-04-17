from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from virtual_staff.memory_builder import DEFAULT_TAGS, SharedMemoryBuilder
from virtual_staff.orchestrator import OrchestratorAgent
from virtual_staff.tag_store import SQLiteTagStore


def _prepare_sqlite_state(tag_store: SQLiteTagStore, updates: Dict[str, float], correlation_id: str) -> None:
    tag_store.seed_defaults_if_empty(DEFAULT_TAGS)
    for tag, value in updates.items():
        tag_store.insert_sample(
            tag=tag,
            value=value,
            quality="good",
            source="mvp1_readiness",
            correlation_id=correlation_id,
        )


def _run_case(
    case_name: str,
    tag_updates: Dict[str, float],
    active_alarms: List[Dict[str, str]],
    orchestrator: OrchestratorAgent,
    builder: SharedMemoryBuilder,
    tag_store: SQLiteTagStore,
) -> Dict[str, Any]:
    _prepare_sqlite_state(tag_store, tag_updates, correlation_id=case_name)
    memory = builder.build(active_alarms=active_alarms)
    result = orchestrator.run_cycle(memory, case_name=case_name)
    selected = result.get("selected_action")
    return {
        "case_name": case_name,
        "selected_score": None if selected is None else selected.get("score"),
        "selected_candidate": None if selected is None else selected.get("candidate"),
        "selected_runtime_mode": None
        if selected is None
        else selected.get("sim_output", {}).get("runtime_mode"),
        "ranked_count": len(result.get("ranked_options", [])),
        "rejected_count": len(result.get("rejected_options", [])),
    }


def main() -> None:
    tag_store = SQLiteTagStore()
    builder = SharedMemoryBuilder(tag_store=tag_store)
    orchestrator = OrchestratorAgent(tag_store=tag_store)

    scenarios = [
        {
            "case_name": "mvp1_normal",
            "tag_updates": {
                "heater.feed_flow_kg_s": 100.0,
                "heater.stack_temp_c": 248.0,
            },
            "active_alarms": [],
        },
        {
            "case_name": "mvp1_alarm",
            "tag_updates": {
                "heater.stack_temp_c": 292.0,
            },
            "active_alarms": [{"code": "HIGH_STACK_TEMP", "severity": "high"}],
        },
        {
            "case_name": "mvp1_conflict",
            "tag_updates": {
                "heater.stack_temp_c": 325.0,
                "heater.feed_flow_kg_s": 120.0,
            },
            "active_alarms": [],
        },
    ]

    summary = [
        _run_case(
            case_name=scenario["case_name"],
            tag_updates=scenario["tag_updates"],
            active_alarms=scenario["active_alarms"],
            orchestrator=orchestrator,
            builder=builder,
            tag_store=tag_store,
        )
        for scenario in scenarios
    ]

    out_path = Path("ops_events") / "mvp1_readiness_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"summary_path": str(out_path), "cases": summary}, indent=2))


if __name__ == "__main__":
    main()
