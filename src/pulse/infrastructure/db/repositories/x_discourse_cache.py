from typing import Optional

from pulse.infrastructure.db.d1 import DatabaseClient
from pulse.types import CachedXDiscourse, Discourse

GET_CACHED_DISCOURSE_QUERY = """
SELECT conversation_id, discourse_json, latest_post_id, refreshed_at
FROM x_discourse_cache
WHERE conversation_id = ?1
LIMIT 1;
"""

UPSERT_CACHED_DISCOURSE_QUERY = """
INSERT INTO x_discourse_cache (
    conversation_id,
    discourse_json,
    latest_post_id,
    refreshed_at
)
VALUES (?1, ?2, ?3, ?4)
ON CONFLICT(conversation_id)
DO UPDATE SET
    discourse_json = excluded.discourse_json,
    latest_post_id = excluded.latest_post_id,
    refreshed_at = excluded.refreshed_at;
"""


class XDiscourseCacheRepository:
    def __init__(self, *, db_client: DatabaseClient) -> None:
        self.db_client = db_client

    async def get(
        self,
        *,
        conversation_id: str,
    ) -> Optional[CachedXDiscourse]:
        rows = await self.db_client.query(
            sql=GET_CACHED_DISCOURSE_QUERY,
            params=[conversation_id],
        )

        if not rows:
            return None

        row = rows[0]

        return CachedXDiscourse(
            conversation_id=row["conversation_id"],
            discourse=Discourse.model_validate_json(row["discourse_json"]),
            latest_post_id=row["latest_post_id"],
            refreshed_at=row["refreshed_at"],
        )

    async def persist(
        self,
        *,
        cached_discourse: CachedXDiscourse,
    ) -> None:
        await self.db_client.execute(
            sql=UPSERT_CACHED_DISCOURSE_QUERY,
            params=[
                cached_discourse.conversation_id,
                cached_discourse.discourse.model_dump_json(),
                cached_discourse.latest_post_id,
                cached_discourse.refreshed_at.isoformat(),
            ],
        )
