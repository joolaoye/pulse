from typing import Any, cast

import pytest

from pulse.services.interests.interest_embedder import InterestEmbedder


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.model_name = "voyage-test"

    async def embed(
        self,
        text: str,
    ) -> list[float]:
        self.texts.append(text)
        return [float(len(self.texts)), 0.0]


def _embedder() -> tuple[InterestEmbedder, FakeEmbeddingProvider]:
    provider = FakeEmbeddingProvider()
    embedder = InterestEmbedder(
        embedding_provider=cast(Any, provider),
    )
    return embedder, provider


async def test_profile_sections_are_embedded_without_changing_content() -> None:
    embedder, provider = _embedder()

    interests = await embedder.embed_markdown(
        """# AI Infrastructure

Interested in inference systems.
use # tags inside the body.

# Skipped

# Developer Tools

Interested in coding agents.
""",
    )

    assert [(interest.title, interest.content, interest.embedding) for interest in interests] == [
        (
            "AI Infrastructure",
            "Interested in inference systems.\nuse # tags inside the body.",
            [1.0, 0.0],
        ),
        (
            "Developer Tools",
            "Interested in coding agents.",
            [2.0, 0.0],
        ),
    ]
    assert provider.texts == [interest.content for interest in interests]
    assert {interest.embedding_version for interest in interests} == {"voyage-test"}
    assert len({interest.interest_id for interest in interests}) == len(interests)


@pytest.mark.parametrize(
    "markdown",
    [
        "",
        "   \n\n",
        "# Title only\n",
        "# Title only\n\n   ",
    ],
)
async def test_profile_without_interest_bodies_embeds_nothing(
    markdown: str,
) -> None:
    embedder, provider = _embedder()

    assert await embedder.embed_markdown(markdown) == []
    assert provider.texts == []
