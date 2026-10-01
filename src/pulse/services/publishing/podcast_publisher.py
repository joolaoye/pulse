from pydantic import HttpUrl

from pulse.infrastructure.db.repositories import EpisodePublicationRepository
from pulse.services.publishing.rss_publisher import RssFeedPublisher
from pulse.services.publishing.rss_renderer import RssFeedRenderer
from pulse.types import (
    EpisodePublication,
    EpisodePublicationRequest,
    PodcastShow,
    PublicationResult,
)


class PodcastPublisher:
    def __init__(
        self,
        *,
        episode_publication_repository: EpisodePublicationRepository,
        rss_feed_renderer: RssFeedRenderer,
        rss_feed_publisher: RssFeedPublisher,
    ) -> None:
        self.episode_publication_repository = episode_publication_repository
        self.rss_feed_renderer = rss_feed_renderer
        self.rss_feed_publisher = rss_feed_publisher

    async def publish(
        self,
        *,
        podcast_show: PodcastShow,
        publication_request: EpisodePublicationRequest,
    ) -> PublicationResult:
        if podcast_show.show_id != publication_request.show_id:
            raise ValueError(
                "The episode publication request must target the supplied "
                f"podcast show. Podcast show: {podcast_show.show_id}. "
                f"Publication request: {publication_request.show_id}."
            )

        stored_audio = publication_request.stored_audio

        episode_publication = EpisodePublication(
            show_id=publication_request.show_id,
            episode_id=publication_request.episode_id,
            guid=f"urn:pulse:{publication_request.show_id}:{publication_request.episode_id}",
            title=publication_request.title,
            description=publication_request.description,
            published_at=publication_request.published_at,
            duration_seconds=stored_audio.duration_seconds,
            audio_object_key=stored_audio.object_key,
            audio_size_bytes=stored_audio.size_bytes,
            audio_content_type=stored_audio.content_type,
        )

        await self.episode_publication_repository.upsert(
            episode_publication=episode_publication,
        )

        episode_publications = await self.episode_publication_repository.list_for_feed(
            show_id=podcast_show.show_id,
        )

        rendered_feed = self.rss_feed_renderer.render(
            podcast_show=podcast_show,
            episode_publications=episode_publications,
        )

        await self.rss_feed_publisher.publish(
            podcast_show=podcast_show,
            rendered_feed=rendered_feed,
        )

        return PublicationResult(
            show_id=episode_publication.show_id,
            episode_id=episode_publication.episode_id,
            guid=episode_publication.guid,
            audio_url=HttpUrl(
                podcast_show.build_public_url(
                    object_key=episode_publication.audio_object_key,
                )
            ),
            feed_url=HttpUrl(podcast_show.get_feed_url()),
            published_at=episode_publication.published_at,
        )
