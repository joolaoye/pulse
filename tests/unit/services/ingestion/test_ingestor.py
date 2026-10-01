from typing import Any, cast

import pytest

from pulse.services.ingestion.ingestor import Ingestor
from pulse.types import Discourse, DiscourseType, Signal, Tweet


class FakeExactDeduplicator:
    def __init__(
        self,
        known_ids: set[str] | None = None,
    ) -> None:
        self.known_ids = known_ids or set()

    async def exists(
        self,
        signal: Signal,
    ) -> bool:
        return signal.id in self.known_ids


def _standalone(
    tweet_id: str,
    text: str,
) -> Discourse:
    root = Tweet(
        id=tweet_id,
        text=text,
    )

    return Discourse(
        discourse_type=DiscourseType.STANDALONE,
        root_tweet=root,
        tweets=[root],
    )


def _ingestor(
    known_ids: set[str] | None = None,
) -> Ingestor:
    return Ingestor(
        exact_deduplicator=cast(
            Any,
            FakeExactDeduplicator(known_ids),
        ),
    )


async def test_new_signal_survives_ingestion() -> None:
    ingestor = _ingestor()

    result = await ingestor.ingest(
        reconstructed_discourses=[
            _standalone(
                "100",
                "  Launch notes https://t.co/abc  ",
            ),
        ],
    )

    assert result == [
        Signal(
            id="100",
            source="x",
            content="Launch notes",
        ),
    ]


@pytest.mark.parametrize(
    ("known_ids", "discourses", "expected"),
    [
        (
            {"100"},
            [
                _standalone(
                    "100",
                    "Already published",
                ),
            ],
            [],
        ),
        (
            {"100"},
            [
                _standalone(
                    "100",
                    "Already published",
                ),
                _standalone(
                    "100",
                    "Already published again",
                ),
            ],
            [],
        ),
        (
            set(),
            [
                _standalone(
                    "100",
                    "  First report https://t.co/abc ",
                ),
                _standalone(
                    "100",
                    "Second report",
                ),
            ],
            [
                Signal(
                    id="100",
                    source="x",
                    content="First report",
                ),
            ],
        ),
        (
            {"200"},
            [
                _standalone(
                    "100",
                    "Fresh report",
                ),
                _standalone(
                    "200",
                    "Known report",
                ),
                _standalone(
                    "300",
                    "Another fresh report",
                ),
            ],
            [
                Signal(
                    id="100",
                    source="x",
                    content="Fresh report",
                ),
                Signal(
                    id="300",
                    source="x",
                    content="Another fresh report",
                ),
            ],
        ),
    ],
)
async def test_exact_duplicates_do_not_reenter(
    known_ids: set[str],
    discourses: list[Discourse],
    expected: list[Signal],
) -> None:
    ingestor = _ingestor(known_ids)

    result = await ingestor.ingest(
        reconstructed_discourses=discourses,
    )

    assert result == expected


async def test_equivalent_text_does_not_collapse_distinct_source_items() -> None:
    ingestor = _ingestor()

    result = await ingestor.ingest(
        reconstructed_discourses=[
            _standalone(
                "100",
                "Launch notes https://t.co/abc",
            ),
            _standalone(
                "200",
                "  Launch notes  ",
            ),
        ],
    )

    assert result == [
        Signal(
            id="100",
            source="x",
            content="Launch notes",
        ),
        Signal(
            id="200",
            source="x",
            content="Launch notes",
        ),
    ]


async def test_empty_retrieval_returns_no_signals() -> None:
    ingestor = _ingestor()

    result = await ingestor.ingest(
        reconstructed_discourses=[],
    )

    assert result == []
