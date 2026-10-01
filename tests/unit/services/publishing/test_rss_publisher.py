from typing import Any, cast

from pydantic import HttpUrl
import pytest

from pulse.services.publishing.rss_publisher import RSS_FEED_CONTENT_TYPE, RssFeedPublisher
from pulse.types import PodcastShow


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
        public_base_url=HttpUrl("https://podcasts.example.com"),
        feed_object_key="shows/show-1/rss.xml",
    )


async def test_feed_is_uploaded_at_the_show_feed_key() -> None:
    client = FakeR2Client()
    publisher = RssFeedPublisher(
        r2_client=cast(Any, client),
        bucket_name="podcast-bucket",
    )
    rendered_feed = b"<?xml version='1.0'?><rss></rss>"

    await publisher.publish(
        podcast_show=_show(),
        rendered_feed=rendered_feed,
    )

    assert client.uploads == [
        {
            "bucket_name": "podcast-bucket",
            "object_key": "shows/show-1/rss.xml",
            "content": rendered_feed,
            "content_type": RSS_FEED_CONTENT_TYPE,
        }
    ]


async def test_empty_feed_is_rejected_before_upload() -> None:
    client = FakeR2Client()
    publisher = RssFeedPublisher(
        r2_client=cast(Any, client),
        bucket_name="podcast-bucket",
    )

    with pytest.raises(ValueError, match="cannot be empty"):
        await publisher.publish(
            podcast_show=_show(),
            rendered_feed=b"",
        )

    assert client.uploads == []


async def test_upload_failure_is_not_reported_as_success() -> None:
    publisher = RssFeedPublisher(
        r2_client=cast(
            Any,
            FakeR2Client(error=RuntimeError("upload failed")),
        ),
        bucket_name="podcast-bucket",
    )

    with pytest.raises(RuntimeError, match="upload failed"):
        await publisher.publish(
            podcast_show=_show(),
            rendered_feed=b"<rss></rss>",
        )
