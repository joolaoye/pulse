from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Type

import aiosqlite
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from pulse.types import (
    Discourse,
    DiscourseType,
    EmbeddedSignal,
    EpisodeMetadata,
    EpisodeScript,
    NoContentReason,
    PodcastProfile,
    PodcastShow,
    ProcessedSignal,
    PublicationResult,
    Signal,
    SpeakerProfile,
    SpeakerVoiceBinding,
    StoredEpisodeAudio,
    ThemedSignalCluster,
    TurnPlan,
    WorkflowOutcome,
)

_CHECKPOINT_ALLOWED_TYPES: List[Type] = [
    PodcastProfile,
    SpeakerProfile,
    SpeakerVoiceBinding,
    PodcastShow,
    Discourse,
    DiscourseType,
    Signal,
    EmbeddedSignal,
    ProcessedSignal,
    ThemedSignalCluster,
    TurnPlan,
    EpisodeScript,
    EpisodeMetadata,
    StoredEpisodeAudio,
    PublicationResult,
    WorkflowOutcome,
    NoContentReason,
]


@asynccontextmanager
async def create_sqlite_checkpointer(
    *,
    database_path: Path,
) -> AsyncIterator[AsyncSqliteSaver]:
    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serializer = JsonPlusSerializer(
        allowed_msgpack_modules=_CHECKPOINT_ALLOWED_TYPES,
    )

    async with aiosqlite.connect(str(database_path)) as connection:
        yield AsyncSqliteSaver(
            connection,
            serde=serializer,
        )
