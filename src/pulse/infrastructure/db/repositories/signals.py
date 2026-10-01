from typing import Protocol

from pulse.infrastructure.db.d1 import DatabaseClient
from pulse.types import StoredSignal

SIGNAL_EXISTS_QUERY = """
SELECT signal_id
FROM signals
WHERE pipeline_id = ?1
AND source = ?2
AND signal_id = ?3
LIMIT 1;
"""


PERSIST_SIGNAL_QUERY = """
INSERT OR IGNORE INTO signals (
    pipeline_id,
    signal_id,
    source,
    relevance_score
)
VALUES (
    ?1,
    ?2,
    ?3,
    ?4
);
"""


class SignalRepositoryProtocol(Protocol):
    async def persist(
        self,
        *,
        signal: StoredSignal,
    ) -> None: ...


class SignalRepository:
    def __init__(
        self,
        *,
        db_client: DatabaseClient,
        pipeline_id: str,
    ) -> None:
        self.db_client = db_client
        self.pipeline_id = pipeline_id

    async def exists(
        self,
        *,
        source: str,
        signal_id: str,
    ) -> bool:
        rows = await self.db_client.query(
            sql=SIGNAL_EXISTS_QUERY,
            params=[
                self.pipeline_id,
                source,
                signal_id,
            ],
        )

        return bool(rows)

    async def persist(
        self,
        *,
        signal: StoredSignal,
    ) -> None:
        await self.db_client.execute(
            sql=PERSIST_SIGNAL_QUERY,
            params=[
                self.pipeline_id,
                signal.signal_id,
                signal.source,
                str(signal.relevance_score),
            ],
        )
