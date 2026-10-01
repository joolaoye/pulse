from typing import Dict, List

from pulse.infrastructure.db.repositories import (
    SignalRepositoryProtocol,
)
from pulse.infrastructure.vector.repositories import (
    EmbeddedSignalRepositoryProtocol,
)
from pulse.types import (
    EmbeddedSignal,
    ProcessedSignal,
    Signal,
    StoredSignal,
)


class SignalCommitter:
    def __init__(
        self,
        *,
        signal_repository: SignalRepositoryProtocol,
        embedded_signal_repository: EmbeddedSignalRepositoryProtocol,
    ) -> None:
        self.signal_repository = signal_repository
        self.embedded_signal_repository = embedded_signal_repository

    async def commit(
        self,
        *,
        signals: List[Signal],
        embedded_signals_by_id: Dict[str, EmbeddedSignal],
        processed_signals_by_id: Dict[str, ProcessedSignal],
    ) -> None:
        signals_by_id = self._index_signals(signals=signals)

        self._validate_alignment(
            signals_by_id=signals_by_id,
            embedded_signals_by_id=embedded_signals_by_id,
            processed_signals_by_id=processed_signals_by_id,
        )

        for signal_id, processed_signal in processed_signals_by_id.items():
            signal = signals_by_id[signal_id]

            await self.signal_repository.persist(
                signal=StoredSignal(
                    signal_id=processed_signal.signal_id,
                    source=processed_signal.source,
                    relevance_score=processed_signal.relevance_score,
                ),
            )

            await self.embedded_signal_repository.persist(
                signal=signal,
                embedded_signal=embedded_signals_by_id[signal_id],
            )

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
    def _validate_alignment(
        *,
        signals_by_id: Dict[str, Signal],
        embedded_signals_by_id: Dict[str, EmbeddedSignal],
        processed_signals_by_id: Dict[str, ProcessedSignal],
    ) -> None:
        processed_signal_ids = set(processed_signals_by_id)

        missing_signal_ids = processed_signal_ids - set(signals_by_id)

        if missing_signal_ids:
            raise ValueError(
                "Processed signals are missing corresponding signals: "
                f"{sorted(missing_signal_ids)}."
            )

        missing_embedding_ids = processed_signal_ids - set(embedded_signals_by_id)

        if missing_embedding_ids:
            raise ValueError(
                "Processed signals are missing corresponding embeddings: "
                f"{sorted(missing_embedding_ids)}."
            )
