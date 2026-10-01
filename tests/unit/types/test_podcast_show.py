from pydantic import ValidationError
import pytest

from pulse.types import PodcastShow


def _show(
    *,
    public_base_url: str = "https://cdn.example/nightly",
    feed_object_key: str = "shows/show-alpha/feed.xml",
) -> PodcastShow:
    return PodcastShow(
        show_id="show-alpha",
        title="Nightly Pulse",
        description="A show about rates, not weather.",
        author="Ada Lovelace",
        website_url="https://nightly.example/about",
        artwork_url="https://nightly.example/art.png",
        category="Business",
        language="en-GB",
        public_base_url=public_base_url,
        feed_object_key=feed_object_key,
    )


@pytest.mark.parametrize(
    ("feed_object_key", "valid"),
    [
        ("shows/show-alpha/feed.xml", True),
        ("shows/show-alpha/feed.json", False),
    ],
)
def test_feed_object_key_must_identify_an_xml_file(
    feed_object_key: str,
    valid: bool,
) -> None:
    if valid:
        assert _show(feed_object_key=feed_object_key).feed_object_key == feed_object_key
        return

    with pytest.raises(ValidationError):
        _show(feed_object_key=feed_object_key)


@pytest.mark.parametrize(
    "public_base_url",
    [
        "https://example.com/podcasts?foo=bar",
        "https://example.com/podcasts#section",
    ],
)
def test_public_base_url_rejects_query_and_fragment(public_base_url: str) -> None:
    with pytest.raises(ValidationError):
        _show(public_base_url=public_base_url)
