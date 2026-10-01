from typing import Any, cast

import pytest

from pulse.agents.theme_extraction.schemas import ThemeExtractionInput
from pulse.services.grouping.signal_group_builder import SignalGroupBuilder
from pulse.types import (
    EmbeddedSignal,
    ProcessedSignal,
    SignalCluster,
    Theme,
    ThemedSignalCluster,
)


class RecordingThemeAgent:
    def __init__(self) -> None:
        self.signal_ids: list[list[str]] = []

    async def arun(
        self,
        theme_input: ThemeExtractionInput,
    ) -> Theme:
        signal_ids = [signal.signal_id for signal in theme_input.signals]
        self.signal_ids.append(signal_ids)
        return Theme(
            title=f"theme-{signal_ids[0]}",
            summary="shared theme",
        )


class FixedClusterer:
    def __init__(
        self,
        clusters: list[SignalCluster],
    ) -> None:
        self.clusters = clusters

    def cluster(
        self,
        embedded_signals: list[EmbeddedSignal],
    ) -> list[SignalCluster]:
        return self.clusters


class UncalledClusterer:
    def cluster(
        self,
        embedded_signals: list[EmbeddedSignal],
    ) -> list[SignalCluster]:
        raise AssertionError("empty input must not be clustered")


def _processed(
    signal_id: str,
    relevance_score: float,
) -> ProcessedSignal:
    return ProcessedSignal(
        signal_id=signal_id,
        title=signal_id,
        markdown_context=f"context {signal_id}",
        relevance_score=relevance_score,
        source="x",
    )


def _embedded(
    signal_id: str,
) -> EmbeddedSignal:
    return EmbeddedSignal(
        signal_id=signal_id,
        embedding=[1.0, 0.0],
        embedding_version="test",
    )


def _builder(
    clusterer: object,
    agent: RecordingThemeAgent | None = None,
) -> tuple[SignalGroupBuilder, RecordingThemeAgent]:
    theme_agent = agent or RecordingThemeAgent()
    builder = SignalGroupBuilder(
        signal_clusterer=cast(Any, clusterer),
        theme_extraction_agent=cast(Any, theme_agent),
    )
    return builder, theme_agent


async def test_themes_and_relevance_stay_with_cluster_members() -> None:
    builder, agent = _builder(
        FixedClusterer(
            [
                SignalCluster(
                    cluster_id=0,
                    signal_ids=["a", "b", "c", "d"],
                ),
                SignalCluster(
                    cluster_id=1,
                    signal_ids=["e"],
                ),
            ]
        )
    )
    processed = {
        "a": _processed("a", 0.2),
        "b": _processed("b", 0.9),
        "c": _processed("c", 0.1),
        "d": _processed("d", 0.4),
        "e": _processed("e", 0.8),
    }

    groups = await builder.build(
        embedded_signals=[_embedded(signal_id) for signal_id in ("e", "a", "d", "b", "c")],
        processed_signals=[processed[signal_id] for signal_id in ("c", "e", "a", "d", "b")],
    )

    assert groups == [
        ThemedSignalCluster(
            cluster_id=0,
            relevance_score=(0.9 + 0.4 + 0.2) / 3,
            theme=Theme(
                title="theme-a",
                summary="shared theme",
            ),
            signal_ids=["a", "b", "c", "d"],
        ),
        ThemedSignalCluster(
            cluster_id=1,
            relevance_score=0.8,
            theme=Theme(
                title="theme-e",
                summary="shared theme",
            ),
            signal_ids=["e"],
        ),
    ]
    assert agent.signal_ids == [
        ["a", "b", "c", "d"],
        ["e"],
    ]


async def test_empty_input_returns_no_groups() -> None:
    builder, agent = _builder(UncalledClusterer())

    assert (
        await builder.build(
            embedded_signals=[],
            processed_signals=[],
        )
        == []
    )
    assert agent.signal_ids == []


async def test_mismatched_signal_ids_are_rejected() -> None:
    builder, _agent = _builder(
        FixedClusterer(
            [
                SignalCluster(
                    cluster_id=0,
                    signal_ids=["a"],
                )
            ]
        )
    )

    with pytest.raises(ValueError, match="same signal IDs"):
        await builder.build(
            embedded_signals=[_embedded("a")],
            processed_signals=[_processed("b", 0.5)],
        )
