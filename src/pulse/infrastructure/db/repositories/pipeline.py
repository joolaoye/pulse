import json
from typing import Any, Dict, List, Optional

from pulse.infrastructure.db.d1 import DatabaseClient
from pulse.types import (
    PodcastPipeline,
    PodcastProfile,
    SpeakerProfile,
    SpeakerVoiceBinding,
)

CREATE_PODCAST_PIPELINE_QUERY = """
INSERT INTO podcast_pipeline (
    pipeline_id,
    show_id,
    podcast_profile_json,
    speakers_json,
    speaker_voice_bindings_json,
    interest_profile_markdown,
    x_list_id,
    target_episode_duration_seconds,
    enabled
)
VALUES (
    ?1,
    ?2,
    ?3,
    ?4,
    ?5,
    ?6,
    ?7,
    ?8,
    ?9
);
"""


GET_PODCAST_PIPELINE_QUERY = """
SELECT
    pipeline_id,
    show_id,
    podcast_profile_json,
    speakers_json,
    speaker_voice_bindings_json,
    interest_profile_markdown,
    x_list_id,
    target_episode_duration_seconds,
    enabled
FROM podcast_pipeline
WHERE pipeline_id = ?1;
"""


LIST_PODCAST_PIPELINES_QUERY = """
SELECT
    pipeline_id,
    show_id,
    podcast_profile_json,
    speakers_json,
    speaker_voice_bindings_json,
    interest_profile_markdown,
    x_list_id,
    target_episode_duration_seconds,
    enabled
FROM podcast_pipeline
ORDER BY pipeline_id ASC;
"""


UPDATE_PODCAST_PIPELINE_QUERY = """
UPDATE podcast_pipeline
SET
    show_id = ?2,
    podcast_profile_json = ?3,
    speakers_json = ?4,
    speaker_voice_bindings_json = ?5,
    interest_profile_markdown = ?6,
    x_list_id = ?7,
    target_episode_duration_seconds = ?8,
    enabled = ?9,
    updated_at = strftime(
        '%Y-%m-%dT%H:%M:%fZ',
        'now'
    )
WHERE pipeline_id = ?1;
"""


SET_PODCAST_PIPELINE_ENABLED_QUERY = """
UPDATE podcast_pipeline
SET
    enabled = ?2,
    updated_at = strftime(
        '%Y-%m-%dT%H:%M:%fZ',
        'now'
    )
WHERE pipeline_id = ?1;
"""


class PodcastPipelineRepository:
    def __init__(
        self,
        *,
        db_client: DatabaseClient,
    ) -> None:
        self.db_client = db_client

    async def create(
        self,
        *,
        pipeline: PodcastPipeline,
    ) -> None:
        await self.db_client.execute(
            sql=CREATE_PODCAST_PIPELINE_QUERY,
            params=self._serialize_pipeline(
                pipeline=pipeline,
            ),
        )

    async def get(
        self,
        *,
        pipeline_id: str,
    ) -> Optional[PodcastPipeline]:
        rows = await self.db_client.query(
            sql=GET_PODCAST_PIPELINE_QUERY,
            params=[pipeline_id],
        )

        if not rows:
            return None

        return self._deserialize_pipeline(
            row=rows[0],
        )

    async def list(self) -> List[PodcastPipeline]:
        rows = await self.db_client.query(
            sql=LIST_PODCAST_PIPELINES_QUERY,
            params=[],
        )

        return [self._deserialize_pipeline(row=row) for row in rows]

    async def update(
        self,
        *,
        pipeline: PodcastPipeline,
    ) -> None:
        await self.db_client.execute(
            sql=UPDATE_PODCAST_PIPELINE_QUERY,
            params=self._serialize_pipeline(
                pipeline=pipeline,
            ),
        )

    async def set_enabled(
        self,
        *,
        pipeline_id: str,
        enabled: bool,
    ) -> None:
        await self.db_client.execute(
            sql=SET_PODCAST_PIPELINE_ENABLED_QUERY,
            params=[
                pipeline_id,
                str(int(enabled)),
            ],
        )

    @staticmethod
    def _serialize_pipeline(
        *,
        pipeline: PodcastPipeline,
    ) -> List[Any]:
        podcast_profile_json = pipeline.podcast_profile.model_dump_json()

        speakers_json = json.dumps(
            [speaker.model_dump(mode="json") for speaker in pipeline.speakers],
            ensure_ascii=False,
        )

        speaker_voice_bindings_json = json.dumps(
            [binding.model_dump(mode="json") for binding in pipeline.speaker_voice_bindings],
            ensure_ascii=False,
        )

        return [
            pipeline.pipeline_id,
            pipeline.show_id,
            podcast_profile_json,
            speakers_json,
            speaker_voice_bindings_json,
            pipeline.interest_profile_markdown,
            pipeline.x_list_id,
            pipeline.target_episode_duration_seconds,
            int(pipeline.enabled),
        ]

    @staticmethod
    def _deserialize_pipeline(
        *,
        row: Dict[str, Any],
    ) -> PodcastPipeline:
        podcast_profile = PodcastProfile.model_validate_json(row["podcast_profile_json"])

        speakers = [
            SpeakerProfile.model_validate(value) for value in json.loads(row["speakers_json"])
        ]

        speaker_voice_bindings = [
            SpeakerVoiceBinding.model_validate(value)
            for value in json.loads(row["speaker_voice_bindings_json"])
        ]

        return PodcastPipeline(
            pipeline_id=row["pipeline_id"],
            show_id=row["show_id"],
            podcast_profile=podcast_profile,
            speakers=speakers,
            speaker_voice_bindings=speaker_voice_bindings,
            interest_profile_markdown=row["interest_profile_markdown"],
            x_list_id=row["x_list_id"],
            target_episode_duration_seconds=int(row["target_episode_duration_seconds"]),
            enabled=bool(int(row["enabled"])),
        )
