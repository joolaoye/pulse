from typing import List

from pulse.services.signals.similarity import cosine_similarity
from pulse.types import (
    EmbeddedInterest,
    EmbeddedSignal,
    InterestMatch,
    ScoredSignal,
)

DEFAULT_TOP_INTEREST_WEIGHT = 0.7
DEFAULT_SECOND_INTEREST_WEIGHT = 0.3


class SignalScorer:
    def __init__(
        self,
        *,
        top_interest_weight: float = DEFAULT_TOP_INTEREST_WEIGHT,
        second_interest_weight: float = DEFAULT_SECOND_INTEREST_WEIGHT,
    ) -> None:
        self.top_interest_weight = top_interest_weight
        self.second_interest_weight = second_interest_weight

    def score_signal(
        self,
        *,
        signal: EmbeddedSignal,
        interests: List[EmbeddedInterest],
    ) -> ScoredSignal:
        interest_matches = [
            InterestMatch(
                interest_id=interest.interest_id,
                title=interest.title,
                relevance_score=cosine_similarity(
                    signal.embedding,
                    interest.embedding,
                ),
            )
            for interest in interests
        ]

        interest_matches.sort(
            key=lambda match: match.relevance_score,
            reverse=True,
        )

        return ScoredSignal(
            signal_id=signal.signal_id,
            relevance_score=self._compute_relevance_score(interest_matches),
            interest_matches=interest_matches,
        )

    def _compute_relevance_score(
        self,
        interest_matches: List[InterestMatch],
    ) -> float:
        scores = [match.relevance_score for match in interest_matches]

        if not scores:
            return 0.0

        if len(scores) == 1:
            return scores[0]

        return self.top_interest_weight * scores[0] + self.second_interest_weight * scores[1]
