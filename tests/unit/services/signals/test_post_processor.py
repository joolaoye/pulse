import asyncio
from typing import List, cast

from pulse.services.signals.canonicalizer import (
    XGenerationCanonicalizer,
)
from pulse.services.signals.post_processor import (
    PostProcessor,
)
from pulse.services.signals.signal_augmenter import (
    XSignalAugmenter,
)
from pulse.services.signals.signal_filter import (
    SignalFilter,
)
from pulse.services.signals.signal_scorer import (
    SignalScorer,
)
from pulse.types import (
    AugmentedXSignal,
    EmbeddedSignal,
    ProcessedSignal,
    ScoredSignal,
    Signal,
)


class FakeSignalScorer:
    def __init__(self) -> None:
        self.scored_signal_ids: List[str] = []

    def score_signal(
        self,
        *,
        signal: EmbeddedSignal,
        interests,
    ) -> ScoredSignal:
        self.scored_signal_ids.append(signal.signal_id)

        scores = {
            "signal-1": 0.91,
            "signal-2": 0.42,
            "signal-3": 0.84,
        }

        return ScoredSignal(
            signal_id=signal.signal_id,
            relevance_score=scores[signal.signal_id],
            interest_matches=[],
        )


class FakeSignalFilter:
    def __init__(self) -> None:
        self.received_signal_ids: List[str] = []

    def filter(
        self,
        scored_signals: List[ScoredSignal],
    ) -> List[ScoredSignal]:
        self.received_signal_ids = [signal.signal_id for signal in scored_signals]

        return [signal for signal in scored_signals if signal.relevance_score >= 0.8]


class FakeSignalAugmenter:
    def __init__(self) -> None:
        self.augmented_signal_ids: List[str] = []

    async def augment(
        self,
        *,
        scored_signal: ScoredSignal,
    ) -> AugmentedXSignal:
        self.augmented_signal_ids.append(scored_signal.signal_id)

        return AugmentedXSignal(
            signal_id=scored_signal.signal_id,
            author_username="test-author",
            top_comments=["Test comment."],
        )


async def _test_processes_only_selected_signals(
    monkeypatch,
) -> None:
    scorer = FakeSignalScorer()
    signal_filter = FakeSignalFilter()
    augmenter = FakeSignalAugmenter()

    canonicalized_signal_ids: List[str] = []

    def fake_canonicalize(
        *,
        signal: Signal,
        scored_signal: ScoredSignal,
        augmented_signal: AugmentedXSignal,
    ) -> ProcessedSignal:
        canonicalized_signal_ids.append(signal.id)

        assert augmented_signal.signal_id == signal.id

        return ProcessedSignal(
            signal_id=signal.id,
            title=f"Title for {signal.id}",
            markdown_context=signal.content,
            relevance_score=(scored_signal.relevance_score),
            source=signal.source,
        )

    monkeypatch.setattr(
        XGenerationCanonicalizer,
        "canonicalize",
        fake_canonicalize,
    )

    post_processor = PostProcessor(
        signal_scorer=cast(
            SignalScorer,
            scorer,
        ),
        signal_filter=cast(
            SignalFilter,
            signal_filter,
        ),
        signal_augmenter=cast(
            XSignalAugmenter,
            augmenter,
        ),
        embedded_interests=[],
    )

    signals = [
        Signal(
            id="signal-1",
            source="x",
            content="Signal one.",
        ),
        Signal(
            id="signal-2",
            source="x",
            content="Signal two.",
        ),
        Signal(
            id="signal-3",
            source="x",
            content="Signal three.",
        ),
    ]

    embedded_signals = [
        EmbeddedSignal(
            signal_id="signal-1",
            embedding=[1.0, 0.0],
            embedding_version="test",
        ),
        EmbeddedSignal(
            signal_id="signal-2",
            embedding=[0.0, 1.0],
            embedding_version="test",
        ),
        EmbeddedSignal(
            signal_id="signal-3",
            embedding=[0.5, 0.5],
            embedding_version="test",
        ),
    ]

    result = await post_processor.process(
        signals=signals,
        embedded_signals=embedded_signals,
    )

    assert scorer.scored_signal_ids == [
        "signal-1",
        "signal-2",
        "signal-3",
    ]

    assert signal_filter.received_signal_ids == [
        "signal-1",
        "signal-2",
        "signal-3",
    ]

    assert augmenter.augmented_signal_ids == [
        "signal-1",
        "signal-3",
    ]

    assert canonicalized_signal_ids == [
        "signal-1",
        "signal-3",
    ]

    assert [signal.signal_id for signal in result] == [
        "signal-1",
        "signal-3",
    ]

    assert [signal.relevance_score for signal in result] == [
        0.91,
        0.84,
    ]


def test_processes_only_selected_signals(
    monkeypatch,
) -> None:
    asyncio.run(
        _test_processes_only_selected_signals(
            monkeypatch,
        )
    )


class RejectAllSignalFilter:
    def filter(
        self,
        scored_signals: List[ScoredSignal],
    ) -> List[ScoredSignal]:
        return []


async def _test_returns_empty_when_all_signals_filtered() -> None:
    scorer = FakeSignalScorer()
    augmenter = FakeSignalAugmenter()

    post_processor = PostProcessor(
        signal_scorer=cast(
            SignalScorer,
            scorer,
        ),
        signal_filter=cast(
            SignalFilter,
            RejectAllSignalFilter(),
        ),
        signal_augmenter=cast(
            XSignalAugmenter,
            augmenter,
        ),
        embedded_interests=[],
    )

    signal = Signal(
        id="signal-1",
        source="x",
        content="Signal one.",
    )

    embedded_signal = EmbeddedSignal(
        signal_id="signal-1",
        embedding=[1.0, 0.0],
        embedding_version="test",
    )

    result = await post_processor.process(
        signals=[signal],
        embedded_signals=[embedded_signal],
    )

    assert result == []
    assert augmenter.augmented_signal_ids == []


def test_returns_empty_when_all_signals_filtered() -> None:
    asyncio.run(_test_returns_empty_when_all_signals_filtered())
