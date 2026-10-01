from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Sequence

from pulse.infrastructure.db.repositories.signals import SignalRepository
from pulse.types import StoredSignal

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "d1"


def _normalize_sql(sql: str) -> str:
    return re.sub(r"\?\d+", "?", sql)


class SqliteDatabaseClient:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript((MIGRATIONS / "0004_create_signals.sql").read_text())

    async def query(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> List[Dict[str, Any]]:
        cursor = self.connection.execute(_normalize_sql(sql), params or [])
        return [dict(row) for row in cursor.fetchall()]

    async def execute(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> None:
        self.connection.execute(_normalize_sql(sql), params or [])
        self.connection.commit()


async def test_signal_identity_is_pipeline_source_and_id_and_persists_once() -> None:
    client = SqliteDatabaseClient()
    repository = SignalRepository(db_client=client, pipeline_id="pipeline-a")
    signal = StoredSignal(signal_id="signal-s", source="x", relevance_score=0.25)

    await repository.persist(signal=signal)
    await repository.persist(
        signal=StoredSignal(signal_id="signal-s", source="x", relevance_score=0.99)
    )

    other_pipeline = SignalRepository(db_client=client, pipeline_id="pipeline-b")
    rows = await client.query(
        "SELECT relevance_score FROM signals WHERE pipeline_id = ?1 AND source = ?2 AND signal_id = ?3",
        ["pipeline-a", "x", "signal-s"],
    )

    assert await repository.exists(source="x", signal_id="signal-s") is True
    assert await repository.exists(source="news", signal_id="signal-s") is False
    assert await other_pipeline.exists(source="x", signal_id="signal-s") is False
    assert rows == [{"relevance_score": 0.25}]
