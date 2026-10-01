from typing import Any, Dict, List, Optional

from pulse.infrastructure.db.d1 import DatabaseClient
from pulse.types import PodcastShow

CREATE_PODCAST_SHOW_QUERY = """
INSERT INTO podcast_show (
    show_id,
    title,
    description,
    author,
    website_url,
    artwork_url,
    category,
    language,
    explicit,
    verification_email,
    public_base_url,
    feed_object_key
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
    ?11,
    ?12
);
"""


GET_PODCAST_SHOW_QUERY = """
SELECT
    show_id,
    title,
    description,
    author,
    website_url,
    artwork_url,
    category,
    language,
    explicit,
    verification_email,
    public_base_url,
    feed_object_key
FROM podcast_show
WHERE show_id = ?1;
"""


LIST_PODCAST_SHOWS_QUERY = """
SELECT
    show_id,
    title,
    description,
    author,
    website_url,
    artwork_url,
    category,
    language,
    explicit,
    verification_email,
    public_base_url,
    feed_object_key
FROM podcast_show
ORDER BY title ASC;
"""


UPDATE_PODCAST_SHOW_QUERY = """
UPDATE podcast_show
SET
    title = ?2,
    description = ?3,
    author = ?4,
    website_url = ?5,
    artwork_url = ?6,
    category = ?7,
    language = ?8,
    explicit = ?9,
    verification_email = ?10,
    public_base_url = ?11,
    feed_object_key = ?12,
    updated_at = strftime(
        '%Y-%m-%dT%H:%M:%fZ',
        'now'
    )
WHERE show_id = ?1;
"""


class PodcastShowRepository:
    def __init__(
        self,
        *,
        db_client: DatabaseClient,
    ) -> None:
        self.db_client = db_client

    async def create(
        self,
        *,
        podcast_show: PodcastShow,
    ) -> None:
        await self.db_client.execute(
            sql=CREATE_PODCAST_SHOW_QUERY,
            params=self._serialize_podcast_show(
                podcast_show=podcast_show,
            ),
        )

    async def get(
        self,
        *,
        show_id: str,
    ) -> Optional[PodcastShow]:
        rows = await self.db_client.query(
            sql=GET_PODCAST_SHOW_QUERY,
            params=[show_id],
        )

        if not rows:
            return None

        return self._deserialize_podcast_show(
            row=rows[0],
        )

    async def list(self) -> List[PodcastShow]:
        rows = await self.db_client.query(
            sql=LIST_PODCAST_SHOWS_QUERY,
            params=[],
        )

        return [self._deserialize_podcast_show(row=row) for row in rows]

    async def update(
        self,
        *,
        podcast_show: PodcastShow,
    ) -> None:
        await self.db_client.execute(
            sql=UPDATE_PODCAST_SHOW_QUERY,
            params=self._serialize_podcast_show(
                podcast_show=podcast_show,
            ),
        )

    @staticmethod
    def _serialize_podcast_show(
        *,
        podcast_show: PodcastShow,
    ) -> List[Any]:
        return [
            podcast_show.show_id,
            podcast_show.title,
            podcast_show.description,
            podcast_show.author,
            str(podcast_show.website_url),
            str(podcast_show.artwork_url),
            podcast_show.category,
            podcast_show.language,
            int(podcast_show.explicit),
            (
                str(podcast_show.verification_email)
                if podcast_show.verification_email is not None
                else None
            ),
            str(podcast_show.public_base_url),
            podcast_show.feed_object_key,
        ]

    @staticmethod
    def _deserialize_podcast_show(
        *,
        row: Dict[str, Any],
    ) -> PodcastShow:
        return PodcastShow(
            show_id=row["show_id"],
            title=row["title"],
            description=row["description"],
            author=row["author"],
            website_url=row["website_url"],
            artwork_url=row["artwork_url"],
            category=row["category"],
            language=row["language"],
            explicit=bool(int(row["explicit"])),
            verification_email=row["verification_email"],
            public_base_url=row["public_base_url"],
            feed_object_key=row["feed_object_key"],
        )
