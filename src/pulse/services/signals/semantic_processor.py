from typing import List

from pulse.services.signals.semantic_deduplicator import SemanticDeduplicator
from pulse.services.signals.signal_embedder import SignalEmbedder
from pulse.types import EmbeddedSignal, Signal


class SemanticProcessor:
    def __init__(
        self,
        *,
        signal_embedder: SignalEmbedder,
        semantic_deduplicator: SemanticDeduplicator,
        index_name: str,
    ) -> None:
        self.signal_embedder = signal_embedder
        self.semantic_deduplicator = semantic_deduplicator
        self.index_name = index_name

    async def process(
        self,
        *,
        signals: List[Signal],
    ) -> List[EmbeddedSignal]:
        embedded_signals: List[EmbeddedSignal] = []

        for signal in signals:
            embedded_signal = await self.signal_embedder.embed_signal(
                signal=signal,
            )

            if self.semantic_deduplicator.is_duplicate_within_run(
                embedded_signal=embedded_signal,
                accepted_signals=embedded_signals,
            ):
                continue

            if await self.semantic_deduplicator.is_duplicate(
                index_name=self.index_name,
                embedded_signal=embedded_signal,
            ):
                continue

            embedded_signals.append(embedded_signal)

        return embedded_signals
