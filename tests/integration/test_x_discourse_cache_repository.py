from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Sequence

from pulse.infrastructure.db.repositories.x_discourse_cache import XDiscourseCacheRepository
from pulse.types import CachedXDiscourse, Discourse, DiscourseType, PublicMetrics, Tweet

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "d1"


def _normalize_sql(sql: str) -> str:
    return re.sub(r"\?\d+", "?", sql)


class SqliteDatabaseClient:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            (MIGRATIONS / "0005_create_x_discourse_cache.sql").read_text()
        )

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


async def test_discourse_cache_roundtrip_preserves_discourse_and_refresh_time() -> None:
    repository = XDiscourseCacheRepository(db_client=SqliteDatabaseClient())
    refreshed_at = datetime(2026, 10, 1, 15, 4, 5, tzinfo=timezone.utc)
    root = Tweet(
        id="root-1",
        text="Rates moved",
        author_id="user-1",
        created_at=datetime(2026, 10, 1, 14, 0, tzinfo=timezone.utc),
        conversation_id="root-1",
        public_metrics=PublicMetrics(like_count=4, retweet_count=1),
    )
    reply = Tweet(
        id="reply-1",
        text="Then the guidance reversed",
        author_id="user-1",
        created_at=datetime(2026, 10, 1, 14, 5, tzinfo=timezone.utc),
        conversation_id="root-1",
        in_reply_to_user_id="user-1",
    )
    cached = CachedXDiscourse(
        conversation_id="root-1",
        discourse=Discourse(
            discourse_type=DiscourseType.THREAD,
            root_tweet=root,
            tweets=[root, reply],
            root_author_username="ada",
        ),
        latest_post_id="reply-1",
        refreshed_at=refreshed_at,
    )

    await repository.persist(cached_discourse=cached)
    stored = await repository.get(conversation_id="root-1")

    assert stored == cached
