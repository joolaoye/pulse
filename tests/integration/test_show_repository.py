from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Sequence

from pulse.infrastructure.db.repositories.show import PodcastShowRepository
from pulse.types import PodcastShow

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "d1"


def _normalize_sql(sql: str) -> str:
    return re.sub(r"\?\d+", "?", sql)


class SqliteDatabaseClient:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript((MIGRATIONS / "0003_create_podcast_show.sql").read_text())

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


def _show() -> PodcastShow:
    return PodcastShow(
        show_id="show-alpha",
        title="Nightly Pulse",
        description="A show about rates, not weather.",
        author="Ada Lovelace",
        website_url="https://nightly.example/about",
        artwork_url="https://nightly.example/art.png",
        category="Business",
        language="en-GB",
        explicit=True,
        verification_email=None,
        public_base_url="https://cdn.example/nightly",
        feed_object_key="shows/show-alpha/feed.xml",
    )


async def test_show_roundtrip_preserves_public_metadata_and_null_email() -> None:
    repository = PodcastShowRepository(db_client=SqliteDatabaseClient())
    show = _show()

    await repository.create(podcast_show=show)
    stored = await repository.get(show_id=show.show_id)

    assert stored == show
    assert stored is not None
    assert stored.verification_email is None
    assert stored.explicit is True
