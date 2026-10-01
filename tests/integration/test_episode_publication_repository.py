from datetime import datetime, timezone
import re
import sqlite3
from typing import Any, Dict, List, Optional, Sequence

import pytest

from pulse.infrastructure.db.repositories.publications import EpisodePublicationRepository
from pulse.types import EpisodePublication


def _normalize_sql(sql: str) -> str:
    return re.sub(r"\?\d+", "?", sql)


class SqliteDatabaseClient:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE episode_publication (
                show_id TEXT NOT NULL,
                episode_id TEXT NOT NULL,
                guid TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                published_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL,
                audio_object_key TEXT NOT NULL,
                audio_size_bytes INTEGER NOT NULL,
                audio_content_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (show_id, episode_id),
                UNIQUE (show_id, guid),
                UNIQUE (show_id, audio_object_key)
            );
            """
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


def _publication(
    *,
    episode_id: str,
    title: str,
    published_at: datetime,
    show_id: str = "show-1",
) -> EpisodePublication:
    return EpisodePublication(
        show_id=show_id,
        episode_id=episode_id,
        guid=f"urn:pulse:{show_id}:{episode_id}",
        title=title,
        description=f"Description for {episode_id}",
        published_at=published_at,
        duration_seconds=60.0,
        audio_object_key=f"shows/{show_id}/episodes/{episode_id}/audio.mp3",
        audio_size_bytes=1024,
        audio_content_type="audio/mpeg",
    )


@pytest.mark.asyncio
async def test_republish_updates_the_same_episode_row() -> None:
    repository = EpisodePublicationRepository(
        db_client=SqliteDatabaseClient(),
    )
    published_at = datetime(2026, 10, 1, tzinfo=timezone.utc)

    await repository.upsert(
        episode_publication=_publication(
            episode_id="episode-1",
            title="First title",
            published_at=published_at,
        )
    )
    original = await repository.get_by_id(
        show_id="show-1",
        episode_id="episode-1",
    )
    assert original is not None

    await repository.upsert(
        episode_publication=_publication(
            episode_id="episode-1",
            title="Revised title",
            published_at=published_at,
        )
    )

    stored = await repository.get_by_id(
        show_id="show-1",
        episode_id="episode-1",
    )
    catalogue = await repository.list_for_feed(show_id="show-1")

    assert stored is not None
    assert stored.title == "Revised title"
    assert stored.guid == "urn:pulse:show-1:episode-1"
    assert stored.created_at == original.created_at
    assert [publication.episode_id for publication in catalogue] == ["episode-1"]


@pytest.mark.asyncio
async def test_feed_catalogue_lists_only_the_show_newest_first() -> None:
    repository = EpisodePublicationRepository(
        db_client=SqliteDatabaseClient(),
    )
    shared_time = datetime(2026, 10, 2, tzinfo=timezone.utc)

    for episode_id, published_at, show_id in (
        ("episode-a", datetime(2026, 10, 1, tzinfo=timezone.utc), "show-1"),
        ("episode-b", shared_time, "show-1"),
        ("episode-c", shared_time, "show-1"),
        ("episode-x", shared_time, "other-show"),
    ):
        await repository.upsert(
            episode_publication=_publication(
                episode_id=episode_id,
                title=episode_id,
                published_at=published_at,
                show_id=show_id,
            )
        )

    catalogue = await repository.list_for_feed(show_id="show-1")

    assert [publication.episode_id for publication in catalogue] == [
        "episode-c",
        "episode-b",
        "episode-a",
    ]
