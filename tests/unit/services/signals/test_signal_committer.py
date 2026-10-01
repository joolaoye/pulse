import asyncio
from typing import List

from pulse.services.signals.signal_committer import SignalCommitter
from pulse.types import EmbeddedSignal, ProcessedSignal, Signal, StoredSignal


class FakeSignalRepository:
    def __init__(self) -> None:
        self.persisted_signals: List[StoredSignal] = []

    async def persist(
        self,
        *,
        signal: StoredSignal,
    ) -> None:
        self.persisted_signals.append(signal)


class FakeEmbeddedSignalRepository:
    def __init__(self) -> None:
        self.persisted = []

    async def persist(
        self,
        *,
        signal,
        embedded_signal,
    ) -> None:
        self.persisted.append((signal, embedded_signal))


async def _test_commits_only_selected_signals() -> None:
    signal_repository = FakeSignalRepository()
    embedded_signal_repository = FakeEmbeddedSignalRepository()

    committer = SignalCommitter(
        signal_repository=signal_repository,
        embedded_signal_repository=(embedded_signal_repository),
    )

    signal_1 = Signal(id="signal-1", source="x", content="Signal one.")
    signal_2 = Signal(id="signal-2", source="x", content="Signal two.")
    signal_3 = Signal(id="signal-3", source="x", content="Signal three.")

    embedding_1 = EmbeddedSignal(
        signal_id="signal-1",
        embedding=[1.0, 0.0],
        embedding_version="test",
    )
    embedding_2 = EmbeddedSignal(
        signal_id="signal-2",
        embedding=[0.0, 1.0],
        embedding_version="test",
    )
    embedding_3 = EmbeddedSignal(
        signal_id="signal-3",
        embedding=[0.5, 0.5],
        embedding_version="test",
    )

    processed_1 = ProcessedSignal.model_construct(
        signal_id="signal-1",
        source="x",
        relevance_score=0.91,
    )
    processed_3 = ProcessedSignal.model_construct(
        signal_id="signal-3",
        source="x",
        relevance_score=0.84,
    )

    await committer.commit(
        signals=[
            signal_1,
            signal_2,
            signal_3,
        ],
        embedded_signals_by_id={
            "signal-1": embedding_1,
            "signal-2": embedding_2,
            "signal-3": embedding_3,
        },
        processed_signals_by_id={
            "signal-1": processed_1,
            "signal-3": processed_3,
        },
    )

    assert [signal.signal_id for signal in signal_repository.persisted_signals] == [
        "signal-1",
        "signal-3",
    ]

    assert [signal.id for signal, _ in embedded_signal_repository.persisted] == [
        "signal-1",
        "signal-3",
    ]

    assert [
        embedded_signal.signal_id for _, embedded_signal in embedded_signal_repository.persisted
    ] == [
        "signal-1",
        "signal-3",
    ]

    assert all(
        signal.id == embedded_signal.signal_id
        for signal, embedded_signal in embedded_signal_repository.persisted
    )


def test_commits_only_selected_signals() -> None:
    asyncio.run(_test_commits_only_selected_signals())


async def _test_rejects_missing_embedding() -> None:
    committer = SignalCommitter(
        signal_repository=FakeSignalRepository(),
        embedded_signal_repository=(FakeEmbeddedSignalRepository()),
    )

    signal = Signal(
        id="signal-1",
        source="x",
        content="Signal one.",
    )

    processed_signal = ProcessedSignal.model_construct(
        signal_id="signal-1",
        source="x",
        relevance_score=0.91,
    )

    try:
        await committer.commit(
            signals=[signal],
            embedded_signals_by_id={},
            processed_signals_by_id={
                "signal-1": processed_signal,
            },
        )
    except ValueError as error:
        assert "signal-1" in str(error)
    else:
        raise AssertionError("Expected missing embedding to raise ValueError.")


def test_rejects_missing_embedding() -> None:
    asyncio.run(_test_rejects_missing_embedding())
