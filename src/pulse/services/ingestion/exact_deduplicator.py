from pulse.infrastructure.db.d1 import D1Client
from pulse.types import Signal


class ExactDeduplicator:
    def __init__(
        self,
        *,
        d1_client: D1Client,
        pipeline_id: str,
    ) -> None:
        self.d1_client = d1_client

        self.pipeline_id = pipeline_id

    async def exists(
        self,
        signal: Signal,
    ) -> bool:
        results = await self.d1_client.query(
            sql="""
                SELECT 1
                FROM signals
                WHERE pipeline_id = ?
                AND source = ?
                AND signal_id = ?
                LIMIT 1
                """,
            params=[
                self.pipeline_id,
                signal.source,
                signal.id,
            ],
        )

        return bool(results)
