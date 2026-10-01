from typing import Dict, List

from pulse.services.signals.canonicalizer import (
    XGenerationCanonicalizer,
)
from pulse.services.signals.signal_augmenter import XSignalAugmenter
from pulse.services.signals.signal_filter import SignalFilter
from pulse.services.signals.signal_scorer import SignalScorer
from pulse.types import (
    EmbeddedInterest,
    EmbeddedSignal,
    ProcessedSignal,
    Signal,
)


class PostProcessor:
    def __init__(
        self,
        *,
        signal_scorer: SignalScorer,
        signal_filter: SignalFilter,
        signal_augmenter: XSignalAugmenter,
        embedded_interests: List[EmbeddedInterest],
    ) -> None:
        self.signal_scorer = signal_scorer
        self.signal_filter = signal_filter
        self.signal_augmenter = signal_augmenter
        self.embedded_interests = embedded_interests

    async def process(
        self,
        *,
        signals: List[Signal],
        embedded_signals: List[EmbeddedSignal],
    ) -> List[ProcessedSignal]:
        signals_by_id = self._index_signals(signals=signals)
        embedded_signals_by_id = self._index_embedded_signals(
            embedded_signals=embedded_signals,
        )

        self._validate_alignment(
            signals_by_id=signals_by_id,
            embedded_signals_by_id=embedded_signals_by_id,
        )

        scored_signals = [
            self.signal_scorer.score_signal(
                signal=embedded_signal,
                interests=self.embedded_interests,
            )
            for embedded_signal in embedded_signals
        ]

        selected_signals = self.signal_filter.filter(scored_signals)

        processed_signals: List[ProcessedSignal] = []

        for scored_signal in selected_signals:
            signal = signals_by_id[scored_signal.signal_id]

            augmented_signal = await self.signal_augmenter.augment(
                scored_signal=scored_signal,
            )

            processed_signals.append(
                XGenerationCanonicalizer.canonicalize(
                    signal=signal,
                    scored_signal=scored_signal,
                    augmented_signal=augmented_signal,
                )
            )

        return processed_signals

    @staticmethod
    def _index_signals(
        *,
        signals: List[Signal],
    ) -> Dict[str, Signal]:
        signals_by_id: Dict[str, Signal] = {}

        for signal in signals:
            if signal.id in signals_by_id:
                raise ValueError(f"Duplicate signal ID: {signal.id}.")

            signals_by_id[signal.id] = signal

        return signals_by_id

    @staticmethod
    def _index_embedded_signals(
        *,
        embedded_signals: List[EmbeddedSignal],
    ) -> Dict[str, EmbeddedSignal]:
        signals_by_id: Dict[str, EmbeddedSignal] = {}

        for signal in embedded_signals:
            if signal.signal_id in signals_by_id:
                raise ValueError(f"Duplicate embedded signal ID: {signal.signal_id}.")

            signals_by_id[signal.signal_id] = signal

        return signals_by_id

    @staticmethod
    def _validate_alignment(
        *,
        signals_by_id: Dict[str, Signal],
        embedded_signals_by_id: Dict[str, EmbeddedSignal],
    ) -> None:
        missing_signal_ids = set(embedded_signals_by_id) - set(signals_by_id)

        if missing_signal_ids:
            raise ValueError(
                f"Embedded signals are missing corresponding signals: {sorted(missing_signal_ids)}."
            )
