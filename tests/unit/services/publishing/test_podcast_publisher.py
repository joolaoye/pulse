from datetime import datetime, timezone
from typing import Any, cast
from xml.etree import ElementTree

from pydantic import HttpUrl
import pytest

from pulse.services.publishing.podcast_publisher import PodcastPublisher
from pulse.services.publishing.rss_publisher import RssFeedPublisher
from pulse.services.publishing.rss_renderer import RssFeedRenderer
from pulse.types import (
    EpisodePublication,
    EpisodePublicationRequest,
    EpisodeTurnTiming,
    PodcastShow,
    StoredEpisodeAudio,
)


class Catalogue:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str], EpisodePublication] = {}

    async def upsert(
        self,
        *,
        episode_publication: EpisodePublication,
    ) -> None:
        self.records[(episode_publication.show_id, episode_publication.episode_id)] = (
            episode_publication
        )

    async def list_for_feed(
        self,
        *,
        show_id: str,
    ) -> list[EpisodePublication]:
        return [
            publication
            for (recorded_show_id, _), publication in self.records.items()
            if recorded_show_id == show_id
        ]


class FakeR2Client:
    def __init__(
        self,
        *,
        error: Exception | None = None,
    ) -> None:
        self.error = error
        self.uploads: list[dict[str, Any]] = []

    async def upload_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        if self.error is not None:
            raise self.error

        self.uploads.append(
            {
                "bucket_name": bucket_name,
                "object_key": object_key,
                "content": content,
                "content_type": content_type,
            }
        )


def _show() -> PodcastShow:
    return PodcastShow(
        show_id="show-1",
        title="Pulse",
        description="A show",
        author="Ada",
        website_url=HttpUrl("https://pulse.example.com"),
        artwork_url=HttpUrl("https://cdn.example.com/artwork.png"),
        category="Technology",
        language="en-US",
        public_base_url=HttpUrl("https://podcasts.example.com/"),
        feed_object_key="shows/show-1/rss.xml",
    )


def _stored_audio(episode_id: str) -> StoredEpisodeAudio:
    return StoredEpisodeAudio(
        object_key=f"shows/show-1/episodes/{episode_id}/audio.mp3",
        output_format="mp3",
        content_type="audio/mpeg",
        duration_seconds=90.0,
        size_bytes=2048,
        turn_timings=[
            EpisodeTurnTiming(
                script_turn_index=0,
                speaker_id="host",
                start_time_seconds=0.0,
                end_time_seconds=90.0,
            )
        ],
    )


def _request(
    show: PodcastShow,
    *,
    episode_id: str,
    title: str,
    published_at: datetime,
) -> EpisodePublicationRequest:
    return EpisodePublicationRequest(
        episode_id=episode_id,
        show_id=show.show_id,
        title=title,
        description=f"Description for {episode_id}",
        published_at=published_at,
        stored_audio=_stored_audio(episode_id),
    )


def _publisher(
    catalogue: Catalogue,
    client: FakeR2Client,
) -> PodcastPublisher:
    return PodcastPublisher(
        episode_publication_repository=cast(Any, catalogue),
        rss_feed_renderer=RssFeedRenderer(),
        rss_feed_publisher=RssFeedPublisher(
            r2_client=cast(Any, client),
            bucket_name="podcast-bucket",
        ),
    )


def _enclosure_urls(feed: bytes) -> list[str]:
    root = ElementTree.fromstring(feed)
    return [enclosure.attrib["url"] for enclosure in root.findall("./channel/item/enclosure")]


async def test_publication_rebuilds_feed_from_public_audio_urls() -> None:
    show = _show()
    catalogue = Catalogue()
    client = FakeR2Client()
    publisher = _publisher(catalogue, client)
    await catalogue.upsert(
        episode_publication=EpisodePublication(
            show_id=show.show_id,
            episode_id="episode-old",
            guid="urn:pulse:show-1:episode-old",
            title="Older episode",
            description="Already published",
            published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            duration_seconds=60.0,
            audio_object_key="shows/show-1/episodes/episode-old/audio.mp3",
            audio_size_bytes=1024,
            audio_content_type="audio/mpeg",
        )
    )

    result = await publisher.publish(
        podcast_show=show,
        publication_request=_request(
            show,
            episode_id="episode-new",
            title="Newer episode",
            published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        ),
    )

    assert result.guid == "urn:pulse:show-1:episode-new"
    assert str(result.audio_url) == (
        "https://podcasts.example.com/shows/show-1/episodes/episode-new/audio.mp3"
    )
    assert str(result.feed_url) == "https://podcasts.example.com/shows/show-1/rss.xml"
    assert client.uploads[0]["object_key"] == "shows/show-1/rss.xml"
    assert _enclosure_urls(client.uploads[0]["content"]) == [
        "https://podcasts.example.com/shows/show-1/episodes/episode-new/audio.mp3",
        "https://podcasts.example.com/shows/show-1/episodes/episode-old/audio.mp3",
    ]


async def test_republishing_the_same_episode_does_not_duplicate_the_feed() -> None:
    show = _show()
    catalogue = Catalogue()
    client = FakeR2Client()
    publisher = _publisher(catalogue, client)

    await publisher.publish(
        podcast_show=show,
        publication_request=_request(
            show,
            episode_id="episode-1",
            title="First title",
            published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        ),
    )
    result = await publisher.publish(
        podcast_show=show,
        publication_request=_request(
            show,
            episode_id="episode-1",
            title="Revised title",
            published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        ),
    )

    root = ElementTree.fromstring(client.uploads[-1]["content"])
    titles = [item.findtext("title") for item in root.findall("./channel/item")]

    assert titles == ["Revised title"]
    assert result.guid == "urn:pulse:show-1:episode-1"
    assert len(catalogue.records) == 1


async def test_show_mismatch_fails_before_persistence_or_upload() -> None:
    show = _show()
    catalogue = Catalogue()
    client = FakeR2Client()
    publisher = _publisher(catalogue, client)
    request = _request(
        show,
        episode_id="episode-1",
        title="Episode",
        published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    ).model_copy(update={"show_id": "other-show"})

    with pytest.raises(ValueError, match="must target the supplied"):
        await publisher.publish(
            podcast_show=show,
            publication_request=request,
        )

    assert catalogue.records == {}
    assert client.uploads == []


async def test_feed_upload_failure_fails_publication() -> None:
    show = _show()
    publisher = _publisher(
        Catalogue(),
        FakeR2Client(error=RuntimeError("upload failed")),
    )

    with pytest.raises(RuntimeError, match="upload failed"):
        await publisher.publish(
            podcast_show=show,
            publication_request=_request(
                show,
                episode_id="episode-1",
                title="Episode",
                published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            ),
        )
