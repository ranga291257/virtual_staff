from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Dict, Iterable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteTagStore:
    def __init__(self, db_path: Path | str = "instrument_data/heater_tags.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tag_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_utc TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    value REAL NOT NULL,
                    quality TEXT NOT NULL DEFAULT 'good',
                    instrument_id TEXT,
                    source TEXT,
                    correlation_id TEXT
                )
                """
            )
            existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(tag_samples)").fetchall()}
            if "instrument_id" not in existing_columns:
                conn.execute("ALTER TABLE tag_samples ADD COLUMN instrument_id TEXT")
            if "source" not in existing_columns:
                conn.execute("ALTER TABLE tag_samples ADD COLUMN source TEXT")
            if "correlation_id" not in existing_columns:
                conn.execute("ALTER TABLE tag_samples ADD COLUMN correlation_id TEXT")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tag_samples_tag_ts ON tag_samples(tag, ts_utc DESC)"
            )
            conn.commit()

    def insert_sample(
        self,
        tag: str,
        value: float,
        quality: str = "good",
        ts_utc: str | None = None,
        instrument_id: str | None = None,
        source: str = "runtime",
        correlation_id: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tag_samples(ts_utc, tag, value, quality, instrument_id, source, correlation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ts_utc or utc_now_iso(), tag, float(value), quality, instrument_id, source, correlation_id),
            )
            conn.commit()

    def latest_values(self, tags: Iterable[str]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        with self._connect() as conn:
            for tag in tags:
                row = conn.execute(
                    "SELECT value FROM tag_samples WHERE tag = ? ORDER BY ts_utc DESC LIMIT 1",
                    (tag,),
                ).fetchone()
                if row is not None:
                    out[tag] = float(row[0])
        return out

    def seed_defaults_if_empty(self, defaults: Dict[str, float]) -> None:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM tag_samples").fetchone()[0]
            if int(count) > 0:
                return
            now = utc_now_iso()
            conn.executemany(
                """
                INSERT INTO tag_samples(ts_utc, tag, value, quality, instrument_id, source, correlation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [(now, tag, float(value), "good", None, "seed", None) for tag, value in defaults.items()],
            )
            conn.commit()
