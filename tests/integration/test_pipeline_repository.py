from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Sequence

from pulse.infrastructure.db.repositories.pipeline import PodcastPipelineRepository
from pulse.infrastructure.db.repositories.show import PodcastShowRepository
from pulse.types import (
    PodcastPipeline,
    PodcastProfile,
    PodcastShow,
    SpeakerProfile,
    SpeakerVoiceBinding,
)

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "d1"


def _normalize_sql(sql: str) -> str:
    return re.sub(r"\?\d+", "?", sql)


class SqliteDatabaseClient:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON;")
        self.connection.executescript(
            (MIGRATIONS / "0003_create_podcast_show.sql").read_text()
            + (MIGRATIONS / "0002_create_podcast_pipeline.sql").read_text()
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
        explicit=False,
        verification_email="ada@nightly.example",
        public_base_url="https://cdn.example/nightly",
        feed_object_key="shows/show-alpha/feed.xml",
    )


def _pipeline() -> PodcastPipeline:
    return PodcastPipeline(
        pipeline_id="pipeline-alpha",
        show_id="show-alpha",
        podcast_profile=PodcastProfile(
            name="Nightly Pulse",
            purpose="Explain rate moves for operators.",
            target_audience="Treasury leads",
            editorial_style="Specific and sourced",
            conversational_style="Direct, with one host and one analyst",
        ),
        speakers=[
            SpeakerProfile(
                speaker_id="host",
                display_name="Mina Cho",
                podcast_role="Host",
                persona="Asks for the mechanism",
                expertise=["markets"],
                speaking_style="Short questions",
            ),
            SpeakerProfile(
                speaker_id="analyst",
                display_name="Jules Berg",
                podcast_role="Analyst",
                persona="Stays with the primary source",
                expertise=["policy", "credit"],
                speaking_style="Concrete examples",
            ),
        ],
        speaker_voice_bindings=[
            SpeakerVoiceBinding(speaker_id="analyst", voice_id="voice-analyst"),
            SpeakerVoiceBinding(speaker_id="host", voice_id="voice-host"),
        ],
        interest_profile_markdown="# Rates\n\nCentral-bank language — and what changed.",
        x_list_id="list-1842",
        target_episode_duration_seconds=900,
        enabled=False,
    )


async def test_pipeline_roundtrip_preserves_configuration() -> None:
    client = SqliteDatabaseClient()
    await PodcastShowRepository(db_client=client).create(podcast_show=_show())
    repository = PodcastPipelineRepository(db_client=client)
    pipeline = _pipeline()

    await repository.create(pipeline=pipeline)
    stored = await repository.get(pipeline_id=pipeline.pipeline_id)

    assert stored == pipeline
