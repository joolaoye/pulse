import pytest

from pulse.services.signals.signal_filter import SignalFilter
from pulse.types import ScoredSignal


def _scored(
    signal_id: str,
    relevance_score: float,
) -> ScoredSignal:
    return ScoredSignal(
        signal_id=signal_id,
        relevance_score=relevance_score,
        interest_matches=[],
    )


@pytest.mark.parametrize(
    ("relevance_score", "kept"),
    [
        (0.50, True),
        (0.499, False),
        (0.501, True),
    ],
)
def test_threshold_keeps_scores_at_or_above_cutoff(
    relevance_score: float,
    kept: bool,
) -> None:
    signal = _scored("signal-1", relevance_score)

    result = SignalFilter().filter([signal])

    assert result == ([signal] if kept else [])


def test_selection_keeps_highest_scores_up_to_the_cap() -> None:
    low = _scored("low", 0.55)
    high = _scored("high", 0.9)
    below = _scored("below", 0.49)
    mid = _scored("mid", 0.8)

    result = SignalFilter(
        relevance_threshold=0.5,
        max_signals=2,
    ).filter([low, high, below, mid])

    assert result == [high, mid]


def test_empty_input_returns_no_signals() -> None:
    assert SignalFilter().filter([]) == []
