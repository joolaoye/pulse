from typing import Any, Dict, List, Optional

from pulse.infrastructure.db.d1 import DatabaseClient
from pulse.types import EpisodePublication

GET_EPISODE_PUBLICATION_QUERY = """
SELECT
    show_id,
    episode_id,
    guid,
    title,
    description,
    published_at,
    duration_seconds,
    audio_object_key,
    audio_size_bytes,
    audio_content_type,
    created_at
FROM episode_publication
WHERE
    show_id = ?1
    AND episode_id = ?2
LIMIT 1;
"""


UPSERT_EPISODE_PUBLICATION_QUERY = """
INSERT INTO episode_publication (
    show_id,
    episode_id,
    guid,
    title,
    description,
    published_at,
    duration_seconds,
    audio_object_key,
    audio_size_bytes,
    audio_content_type,
    created_at
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
    ?9,
    ?10,
    ?11
)
ON CONFLICT (
    show_id,
    episode_id
)
DO UPDATE SET
    guid = excluded.guid,
    title = excluded.title,
    description = excluded.description,
    published_at = excluded.published_at,
    duration_seconds = excluded.duration_seconds,
    audio_object_key = excluded.audio_object_key,
    audio_size_bytes = excluded.audio_size_bytes,
    audio_content_type = excluded.audio_content_type;
"""


LIST_EPISODE_PUBLICATIONS_FOR_FEED_QUERY = """
SELECT
    show_id,
    episode_id,
    guid,
    title,
    description,
    published_at,
    duration_seconds,
    audio_object_key,
    audio_size_bytes,
    audio_content_type,
    created_at
FROM episode_publication
WHERE show_id = ?1
ORDER BY
    published_at DESC,
    episode_id DESC;
"""


class EpisodePublicationRepository:
    def __init__(
        self,
        *,
        db_client: DatabaseClient,
    ) -> None:
        self.db_client = db_client

    async def get_by_id(
        self,
        *,
        show_id: str,
        episode_id: str,
    ) -> Optional[EpisodePublication]:
        self._validate_identifier(
            identifier_name="show_id",
            identifier_value=show_id,
        )
        self._validate_identifier(
            identifier_name="episode_id",
            identifier_value=episode_id,
        )

        rows = await self.db_client.query(
            sql=GET_EPISODE_PUBLICATION_QUERY,
            params=[
                show_id,
                episode_id,
            ],
        )

        if not rows:
            return None

        return self._deserialize(row=rows[0])

    async def upsert(
        self,
        *,
        episode_publication: EpisodePublication,
    ) -> None:
        await self.db_client.execute(
            sql=UPSERT_EPISODE_PUBLICATION_QUERY,
            params=self._serialize(
                episode_publication=episode_publication,
            ),
        )

    async def list_for_feed(
        self,
        *,
        show_id: str,
    ) -> List[EpisodePublication]:
        self._validate_identifier(
            identifier_name="show_id",
            identifier_value=show_id,
        )

        rows = await self.db_client.query(
            sql=LIST_EPISODE_PUBLICATIONS_FOR_FEED_QUERY,
            params=[show_id],
        )

        return [self._deserialize(row=row) for row in rows]

    @staticmethod
    def _serialize(
        *,
        episode_publication: EpisodePublication,
    ) -> List[Any]:
        return [
            episode_publication.show_id,
            episode_publication.episode_id,
            episode_publication.guid,
            episode_publication.title,
            episode_publication.description,
            episode_publication.published_at.isoformat(),
            episode_publication.duration_seconds,
            episode_publication.audio_object_key,
            episode_publication.audio_size_bytes,
            episode_publication.audio_content_type,
            episode_publication.created_at.isoformat(),
        ]

    @staticmethod
    def _deserialize(
        *,
        row: Dict[str, Any],
    ) -> EpisodePublication:
        return EpisodePublication.model_validate(row)

    @staticmethod
    def _validate_identifier(
        *,
        identifier_name: str,
        identifier_value: str,
    ) -> None:
        if not identifier_value.strip():
            raise ValueError(
                "An episode publication repository identifier cannot be empty. "
                f"Identifier: {identifier_name}."
            )
