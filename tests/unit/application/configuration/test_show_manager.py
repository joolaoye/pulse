from pulse.application.configuration.models import PodcastShowUpdate
from pulse.application.configuration.show_manager import ShowManager
from pulse.types import PodcastShow


def _show() -> PodcastShow:
    return PodcastShow(
        show_id="show-alpha",
        title="Nightly Pulse",
        description="A show about rates, not weather.",
        author="Ada Lovelace",
        website_url="https://nightly.example/about",
        artwork_url="https://nightly.example/art.png",
        category="Business",
        language="en-GB",
        explicit=True,
        verification_email="ada@nightly.example",
        public_base_url="https://cdn.example/nightly",
        feed_object_key="shows/show-alpha/feed.xml",
    )


class _ShowRepository:
    def __init__(self, show: PodcastShow) -> None:
        self.show = show
        self.updated: list[PodcastShow] = []

    async def get(self, *, show_id: str) -> PodcastShow | None:
        if self.show.show_id == show_id:
            return self.show
        return None

    async def update(self, *, podcast_show: PodcastShow) -> None:
        self.updated.append(podcast_show)
        self.show = podcast_show


async def test_partial_update_preserves_omitted_show_fields() -> None:
    original = _show()
    repository = _ShowRepository(original)
    manager = ShowManager(podcast_show_repository=repository)

    updated = await manager.update(
        show_id=original.show_id,
        update=PodcastShowUpdate(title="Morning Pulse"),
    )

    assert updated.title == "Morning Pulse"
    assert updated.description == original.description
    assert updated.public_base_url == original.public_base_url
    assert updated.verification_email == original.verification_email
    assert updated.feed_object_key == original.feed_object_key
    assert updated.artwork_url == original.artwork_url
    assert updated.explicit is True
    assert repository.updated == [updated]
