from pulse.infrastructure.storage.r2 import R2Client
from pulse.types import PodcastShow

RSS_FEED_CONTENT_TYPE = "application/rss+xml"


class RssFeedPublisher:
    def __init__(
        self,
        *,
        r2_client: R2Client,
        bucket_name: str,
    ) -> None:
        bucket_name = bucket_name.strip()

        if not bucket_name:
            raise ValueError("RSS feed publisher bucket name cannot be empty.")

        self.r2_client = r2_client
        self.bucket_name = bucket_name

    async def publish(
        self,
        *,
        podcast_show: PodcastShow,
        rendered_feed: bytes,
    ) -> None:
        if not rendered_feed:
            raise ValueError("A rendered RSS feed cannot be empty when published.")

        await self.r2_client.upload_object(
            bucket_name=self.bucket_name,
            object_key=podcast_show.feed_object_key,
            content=rendered_feed,
            content_type=RSS_FEED_CONTENT_TYPE,
        )
