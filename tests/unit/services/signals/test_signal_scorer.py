import pytest

from pulse.services.signals.signal_scorer import SignalScorer
from pulse.types import EmbeddedInterest, EmbeddedSignal


def _interest(
    interest_id: str,
    embedding: list[float],
) -> EmbeddedInterest:
    return EmbeddedInterest(
        interest_id=interest_id,
        title=interest_id,
        content=interest_id,
        embedding=embedding,
        embedding_version="test",
    )


def _signal(
    signal_id: str,
    embedding: list[float],
) -> EmbeddedSignal:
    return EmbeddedSignal(
        signal_id=signal_id,
        embedding=embedding,
        embedding_version="test",
    )


@pytest.mark.parametrize(
    ("interest_embedding", "expected_score"),
    [
        (None, 0.0),
        ([1.0, 0.0], 1.0),
        ([0.6, 0.8], 0.6),
    ],
)
def test_score_with_zero_or_one_interest(
    interest_embedding: list[float] | None,
    expected_score: float,
) -> None:
    interests = []
    if interest_embedding is not None:
        interests = [_interest("only", interest_embedding)]

    scored = SignalScorer().score_signal(
        signal=_signal("signal-a", [1.0, 0.0]),
        interests=interests,
    )

    assert scored.signal_id == "signal-a"
    assert scored.relevance_score == pytest.approx(expected_score)
    assert [match.interest_id for match in scored.interest_matches] == [
        interest.interest_id for interest in interests
    ]


def test_score_uses_strongest_two_matches_for_the_given_signal() -> None:
    scorer = SignalScorer()
    interests = [
        _interest("none", [0.0, 1.0]),
        _interest("partial", [0.6, 0.8]),
        _interest("strong", [1.0, 0.0]),
    ]

    aligned = scorer.score_signal(
        signal=_signal("signal-a", [1.0, 0.0]),
        interests=interests,
    )
    orthogonal = scorer.score_signal(
        signal=_signal("signal-b", [0.0, 1.0]),
        interests=interests,
    )

    assert aligned.signal_id == "signal-a"
    assert aligned.relevance_score == pytest.approx(0.7 * 1.0 + 0.3 * 0.6)
    assert [(match.interest_id, match.relevance_score) for match in aligned.interest_matches] == [
        ("strong", pytest.approx(1.0)),
        ("partial", pytest.approx(0.6)),
        ("none", pytest.approx(0.0)),
    ]

    assert orthogonal.signal_id == "signal-b"
    assert orthogonal.relevance_score == pytest.approx(0.7 * 1.0 + 0.3 * 0.8)
    assert [match.interest_id for match in orthogonal.interest_matches] == [
        "none",
        "partial",
        "strong",
    ]
