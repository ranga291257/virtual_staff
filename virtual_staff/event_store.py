from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
from typing import Any, Dict, List


class OpsEventStore:
    def __init__(self, base_dir: Path | str = "ops_events"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.base_dir / "events.jsonl"

    def _to_jsonable(self, payload: Any) -> Dict[str, Any]:
        if is_dataclass(payload):
            return asdict(payload)
        if isinstance(payload, dict):
            return payload
        return {"value": str(payload)}

    def append(self, event_type: str, payload: Any, correlation: Dict[str, Any] | None = None) -> None:
        record = {"event_type": event_type, "payload": self._to_jsonable(payload)}
        if correlation:
            record["correlation"] = correlation
        with self.events_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def replay(self) -> List[Dict[str, Any]]:
        if not self.events_file.exists():
            return []
        records: List[Dict[str, Any]] = []
        with self.events_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    def replay_by_event(self, event_type: str) -> List[Dict[str, Any]]:
        return [record for record in self.replay() if record.get("event_type") == event_type]
