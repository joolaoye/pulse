from typing import List

from pulse.types import ScoredSignal

DEFAULT_RELEVANCE_THRESHOLD = 0.50
DEFAULT_MAX_SIGNALS = 20


class SignalFilter:
    def __init__(
        self,
        *,
        relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
        max_signals: int = DEFAULT_MAX_SIGNALS,
    ) -> None:
        self.relevance_threshold = relevance_threshold
        self.max_signals = max_signals

    def filter(
        self,
        scored_signals: List[ScoredSignal],
    ) -> List[ScoredSignal]:
        eligible_signals = [
            signal
            for signal in scored_signals
            if signal.relevance_score >= self.relevance_threshold
        ]

        eligible_signals.sort(
            key=lambda signal: signal.relevance_score,
            reverse=True,
        )

        return eligible_signals[: self.max_signals]
