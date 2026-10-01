from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

from pydantic import HttpUrl
import pytest

from pulse.services.publishing.rss_renderer import RssFeedRenderer
from pulse.types import EpisodePublication, PodcastShow

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"


def _show(
    *,
    verification_email: str | None = "ada@example.com",
) -> PodcastShow:
    return PodcastShow(
        show_id="show-1",
        title="Pulse & Co",
        description="Ideas > noise",
        author="Ada",
        website_url=HttpUrl("https://pulse.example.com"),
        artwork_url=HttpUrl("https://cdn.example.com/artwork.png"),
        category="Technology",
        language="en-US",
        explicit=False,
        verification_email=verification_email,
        public_base_url=HttpUrl("https://podcasts.example.com/"),
        feed_object_key="shows/show-1/rss.xml",
    )


def _publication(
    *,
    episode_id: str,
    published_at: datetime,
    title: str = "Episode title",
    description: str = "Episode description",
    guid: str | None = None,
    audio_object_key: str | None = None,
    show_id: str = "show-1",
    duration_seconds: float = 125.6,
    audio_size_bytes: int = 4096,
) -> EpisodePublication:
    return EpisodePublication(
        show_id=show_id,
        episode_id=episode_id,
        guid=guid or f"urn:pulse:{show_id}:{episode_id}",
        title=title,
        description=description,
        published_at=published_at,
        duration_seconds=duration_seconds,
        audio_object_key=(audio_object_key or f"shows/{show_id}/episodes/{episode_id}/audio.mp3"),
        audio_size_bytes=audio_size_bytes,
        audio_content_type="audio/mpeg",
    )


def _channel(feed: bytes) -> ElementTree.Element:
    root = ElementTree.fromstring(feed)
    channel = root.find("channel")
    assert channel is not None
    return channel


def _element(parent: ElementTree.Element, tag: str) -> ElementTree.Element:
    element = parent.find(tag)
    assert element is not None
    return element


def _text(parent: ElementTree.Element, tag: str) -> str:
    element = _element(parent, tag)
    assert element.text is not None
    return element.text


def test_feed_contains_show_metadata_and_public_episode_enclosure() -> None:
    show = _show()
    published_at = datetime(
        2026,
        10,
        1,
        13,
        30,
        tzinfo=timezone(timedelta(hours=-5)),
    )
    publication = _publication(
        episode_id="episode-1",
        published_at=published_at,
        title="Signals & Noise <live>",
        description="A & B > C",
    )

    channel = _channel(
        RssFeedRenderer().render(
            podcast_show=show,
            episode_publications=[publication],
        )
    )

    assert _text(channel, "title") == "Pulse & Co"
    assert _text(channel, "description") == "Ideas > noise"
    assert _text(channel, "link") == str(show.website_url)
    assert _text(channel, "language") == "en-US"
    assert _text(channel, f"{{{ITUNES}}}author") == "Ada"
    assert _text(channel, f"{{{ITUNES}}}explicit") == "false"
    assert _element(channel, f"{{{ITUNES}}}image").attrib["href"] == str(show.artwork_url)
    assert _element(channel, f"{{{ITUNES}}}category").attrib["text"] == "Technology"
    assert _text(channel, f"{{{ITUNES}}}owner/{{{ITUNES}}}email") == "ada@example.com"

    item = channel.find("item")
    assert item is not None
    assert _text(item, "title") == "Signals & Noise <live>"
    assert _text(item, "description") == "A & B > C"
    assert _text(item, "guid") == "urn:pulse:show-1:episode-1"
    assert _element(item, "guid").attrib["isPermaLink"] == "false"
    assert parsedate_to_datetime(_text(item, "pubDate")) == published_at.astimezone(timezone.utc)
    assert _text(item, f"{{{ITUNES}}}duration") == "126"

    enclosure = item.find("enclosure")
    assert enclosure is not None
    assert enclosure.attrib["url"] == (
        "https://podcasts.example.com/shows/show-1/episodes/episode-1/audio.mp3"
    )
    assert "/r2/" not in enclosure.attrib["url"]
    assert enclosure.attrib["type"] == "audio/mpeg"
    assert enclosure.attrib["length"] == "4096"


def test_missing_verification_email_omits_owner() -> None:
    channel = _channel(
        RssFeedRenderer().render(
            podcast_show=_show(verification_email=None),
            episode_publications=[
                _publication(
                    episode_id="episode-1",
                    published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                )
            ],
        )
    )

    assert channel.find(f"{{{ITUNES}}}owner") is None


def test_episodes_are_ordered_newest_first() -> None:
    shared_time = datetime(2026, 10, 2, tzinfo=timezone.utc)
    older = _publication(
        episode_id="episode-a",
        published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    same_time_lower_id = _publication(
        episode_id="episode-b",
        published_at=shared_time,
    )
    same_time_higher_id = _publication(
        episode_id="episode-c",
        published_at=shared_time,
    )

    channel = _channel(
        RssFeedRenderer().render(
            podcast_show=_show(),
            episode_publications=[older, same_time_lower_id, same_time_higher_id],
        )
    )

    items = channel.findall("item")
    assert [_text(item, "guid") for item in items] == [
        "urn:pulse:show-1:episode-c",
        "urn:pulse:show-1:episode-b",
        "urn:pulse:show-1:episode-a",
    ]
    assert [_element(item, "enclosure").attrib["url"] for item in items] == [
        _show().build_public_url(object_key=publication.audio_object_key)
        for publication in (same_time_higher_id, same_time_lower_id, older)
    ]


@pytest.mark.parametrize(
    ("publications", "match"),
    [
        ([], "at least one episode"),
        (
            [
                _publication(
                    episode_id="episode-1",
                    published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                    show_id="other-show",
                )
            ],
            "target podcast show",
        ),
        (
            [
                _publication(
                    episode_id="episode-1",
                    published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                    guid="urn:pulse:shared",
                ),
                _publication(
                    episode_id="episode-2",
                    published_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
                    guid="urn:pulse:shared",
                ),
            ],
            "unique GUID",
        ),
        (
            [
                _publication(
                    episode_id="episode-1",
                    published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                    audio_object_key="shows/show-1/episodes/shared/audio.mp3",
                ),
                _publication(
                    episode_id="episode-2",
                    published_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
                    audio_object_key="shows/show-1/episodes/shared/audio.mp3",
                ),
            ],
            "unique audio object keys",
        ),
    ],
)
def test_invalid_catalogue_is_rejected(
    publications: list[EpisodePublication],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        RssFeedRenderer().render(
            podcast_show=_show(),
            episode_publications=publications,
        )
