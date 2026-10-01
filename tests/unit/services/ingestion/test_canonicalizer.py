import pytest

from pulse.services.ingestion.canonicalizer import XCanonicalizer
from pulse.types import Discourse, DiscourseType, Signal, Tweet


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


def _thread(
    root_id: str,
    *texts: str,
) -> Discourse:
    tweets = [
        Tweet(
            id=root_id if index == 0 else f"{root_id}-{index}",
            text=text,
        )
        for index, text in enumerate(texts)
    ]

    return Discourse(
        discourse_type=DiscourseType.THREAD,
        root_tweet=tweets[0],
        tweets=tweets,
    )


def _quote(
    root_id: str,
    commentary: str,
    referenced_text: str,
    referenced_id: str = "original",
) -> Discourse:
    return Discourse(
        discourse_type=DiscourseType.QUOTE,
        root_tweet=Tweet(
            id=root_id,
            text=commentary,
        ),
        referenced_tweet=Tweet(
            id=referenced_id,
            text=referenced_text,
        ),
    )


def _signal(
    signal_id: str,
    content: str,
) -> Signal:
    return Signal(
        id=signal_id,
        source="x",
        content=content,
    )


@pytest.mark.parametrize(
    ("discourse", "expected"),
    [
        (
            _standalone(
                "post-1",
                "  Launch notes  ",
            ),
            _signal("post-1", "Launch notes"),
        ),
        (
            _standalone(
                "post-1",
                "Launch notes https://t.co/abc123",
            ),
            _signal("post-1", "Launch notes"),
        ),
        (
            _standalone(
                "post-1",
                "See https://t.co/abc now",
            ),
            _signal("post-1", "See now"),
        ),
        (
            _standalone(
                "post-1",
                "Launch   notes",
            ),
            _signal("post-1", "Launch notes"),
        ),
        (
            _standalone(
                "post-1",
                "Launch\t\tnotes",
            ),
            _signal("post-1", "Launch notes"),
        ),
        (
            _standalone(
                "post-1",
                "Launch\n\n\nnotes",
            ),
            _signal("post-1", "Launch\n\nnotes"),
        ),
        (
            _standalone(
                "post-1",
                "Launch\n\nnotes",
            ),
            _signal("post-1", "Launch\n\nnotes"),
        ),
        (
            _thread(
                "root",
                "  Part one https://t.co/abc  ",
                "   https://t.co/skip   ",
                "Part   two",
            ),
            _signal("root", "Part one\n\nPart two"),
        ),
        (
            _thread(
                "root",
                "Part one",
                "Part two",
            ),
            _signal("root", "Part one\n\nPart two"),
        ),
        (
            _quote(
                "quote",
                "  Worth reading https://t.co/abc ",
                "  Original point  ",
            ),
            _signal(
                "quote",
                "Worth reading\n\nOriginal point",
            ),
        ),
        (
            _quote(
                "quote",
                "Worth reading",
                "Original point",
            ),
            _signal(
                "quote",
                "Worth reading\n\nOriginal point",
            ),
        ),
        (
            _quote(
                "quote",
                "   https://t.co/abc  ",
                "Original point",
            ),
            _signal("quote", "Original point"),
        ),
    ],
)
def test_equivalent_source_representations_keep_stable_canonical_identity(
    discourse: Discourse,
    expected: Signal,
) -> None:
    assert XCanonicalizer.canonicalize(discourse=discourse) == expected


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (
            _standalone(
                "post-1",
                "Launch notes",
            ),
            _standalone(
                "post-2",
                "A different announcement",
            ),
        ),
        (
            _thread(
                "root-1",
                "Part one",
                "Part two",
            ),
            _thread(
                "root-2",
                "Other opening",
                "Other continuation",
            ),
        ),
        (
            _quote(
                "quote-1",
                "First take",
                "Shared original",
                "original",
            ),
            _quote(
                "quote-2",
                "Second take",
                "Shared original",
                "original",
            ),
        ),
    ],
)
def test_materially_different_signals_do_not_collapse(
    left: Discourse,
    right: Discourse,
) -> None:
    left_signal = XCanonicalizer.canonicalize(discourse=left)
    right_signal = XCanonicalizer.canonicalize(discourse=right)

    assert left_signal != right_signal
    assert left_signal.id != right_signal.id
