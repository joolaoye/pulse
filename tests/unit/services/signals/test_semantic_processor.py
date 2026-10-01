import asyncio
from typing import Dict, List, Set, cast

from pulse.services.signals.semantic_deduplicator import (
    SemanticDeduplicator,
)
from pulse.services.signals.semantic_processor import (
    SemanticProcessor,
)
from pulse.services.signals.signal_embedder import (
    SignalEmbedder,
)
from pulse.types import (
    EmbeddedSignal,
    Signal,
)


class FakeSignalEmbedder:
    def __init__(
        self,
        *,
        embeddings_by_signal_id: Dict[str, List[float]],
    ) -> None:
        self.embeddings_by_signal_id = embeddings_by_signal_id
        self.embedded_signal_ids: List[str] = []

    async def embed_signal(
        self,
        *,
        signal: Signal,
    ) -> EmbeddedSignal:
        self.embedded_signal_ids.append(signal.id)

        return EmbeddedSignal(
            signal_id=signal.id,
            embedding=(self.embeddings_by_signal_id[signal.id]),
            embedding_version="test",
        )


class FakeSemanticDeduplicator:
    def __init__(
        self,
        *,
        within_run_duplicate_ids: Set[str] | None = None,
        historical_duplicate_ids: Set[str] | None = None,
    ) -> None:
        self.within_run_duplicate_ids = within_run_duplicate_ids or set()
        self.historical_duplicate_ids = historical_duplicate_ids or set()
        self.within_run_checks: List[str] = []
        self.historical_checks: List[str] = []

    def is_duplicate_within_run(
        self,
        *,
        embedded_signal: EmbeddedSignal,
        accepted_signals: List[EmbeddedSignal],
    ) -> bool:
        self.within_run_checks.append(embedded_signal.signal_id)

        return embedded_signal.signal_id in self.within_run_duplicate_ids

    async def is_duplicate(
        self,
        *,
        index_name: str,
        embedded_signal: EmbeddedSignal,
    ) -> bool:
        self.historical_checks.append(embedded_signal.signal_id)

        return embedded_signal.signal_id in self.historical_duplicate_ids


async def _test_rejects_same_run_duplicate_before_historical_check() -> None:
    embedder = FakeSignalEmbedder(
        embeddings_by_signal_id={
            "signal-1": [1.0, 0.0],
            "signal-2": [0.999, 0.001],
        }
    )
    deduplicator = FakeSemanticDeduplicator(
        within_run_duplicate_ids={
            "signal-2",
        },
    )

    processor = SemanticProcessor(
        signal_embedder=cast(
            SignalEmbedder,
            embedder,
        ),
        semantic_deduplicator=cast(
            SemanticDeduplicator,
            deduplicator,
        ),
        index_name="test-index",
    )

    signals = [
        Signal(
            id="signal-1",
            source="x",
            content="First version of the story.",
        ),
        Signal(
            id="signal-2",
            source="x",
            content="Near-duplicate version of the story.",
        ),
    ]

    result = await processor.process(
        signals=signals,
    )

    assert embedder.embedded_signal_ids == [
        "signal-1",
        "signal-2",
    ]

    assert deduplicator.within_run_checks == [
        "signal-1",
        "signal-2",
    ]

    assert deduplicator.historical_checks == [
        "signal-1",
    ]

    assert [signal.signal_id for signal in result] == [
        "signal-1",
    ]


def test_rejects_same_run_duplicate_before_historical_check() -> None:
    asyncio.run(_test_rejects_same_run_duplicate_before_historical_check())


async def _test_rejects_historical_duplicate() -> None:
    embedder = FakeSignalEmbedder(
        embeddings_by_signal_id={
            "signal-1": [1.0, 0.0],
            "signal-2": [0.0, 1.0],
        }
    )

    deduplicator = FakeSemanticDeduplicator(
        historical_duplicate_ids={
            "signal-2",
        },
    )

    processor = SemanticProcessor(
        signal_embedder=cast(
            SignalEmbedder,
            embedder,
        ),
        semantic_deduplicator=cast(
            SemanticDeduplicator,
            deduplicator,
        ),
        index_name="test-index",
    )

    signals = [
        Signal(
            id="signal-1",
            source="x",
            content="A new story.",
        ),
        Signal(
            id="signal-2",
            source="x",
            content="A story already present in history.",
        ),
    ]

    result = await processor.process(
        signals=signals,
    )

    assert embedder.embedded_signal_ids == [
        "signal-1",
        "signal-2",
    ]

    assert deduplicator.within_run_checks == [
        "signal-1",
        "signal-2",
    ]

    assert deduplicator.historical_checks == [
        "signal-1",
        "signal-2",
    ]

    assert [signal.signal_id for signal in result] == [
        "signal-1",
    ]


def test_rejects_historical_duplicate() -> None:
    asyncio.run(_test_rejects_historical_duplicate())
