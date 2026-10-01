from pulse.infrastructure.db.d1 import D1Client
from pulse.infrastructure.db.repositories import EpisodePublicationRepository
from pulse.infrastructure.storage.r2 import R2Client
from pulse.services.publishing import (
    PodcastPublisher,
    RssFeedPublisher,
    RssFeedRenderer,
)


def create_podcast_publisher(
    *,
    d1_client: D1Client,
    r2_client: R2Client,
    bucket_name: str,
) -> PodcastPublisher:
    return PodcastPublisher(
        episode_publication_repository=EpisodePublicationRepository(
            db_client=d1_client,
        ),
        rss_feed_renderer=RssFeedRenderer(),
        rss_feed_publisher=RssFeedPublisher(
            r2_client=r2_client,
            bucket_name=bucket_name,
        ),
    )
