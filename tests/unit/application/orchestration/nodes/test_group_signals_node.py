import pytest

from pulse.application.orchestration.nodes.group_signals_node import GroupSignalsNode
from pulse.types import EmbeddedSignal, ProcessedSignal


class _NodeLogger:
    def node_started(self, **kwargs) -> None:
        del kwargs

    def node_completed(self, **kwargs) -> None:
        del kwargs

    def node_failed(self, **kwargs) -> None:
        del kwargs


def _processed(signal_id: str) -> ProcessedSignal:
    return ProcessedSignal(
        signal_id=signal_id,
        title=signal_id,
        markdown_context=signal_id,
        relevance_score=0.8,
        source="x",
    )


def _embedded(signal_id: str, marker: float) -> EmbeddedSignal:
    return EmbeddedSignal(
        signal_id=signal_id,
        embedding=[marker, 0.0],
        embedding_version="test",
    )


class _GroupBuilder:
    def __init__(self) -> None:
        self.calls: list[tuple[list[EmbeddedSignal], list[ProcessedSignal]]] = []

    async def build(
        self,
        *,
        embedded_signals: list[EmbeddedSignal],
        processed_signals: list[ProcessedSignal],
    ) -> list:
        self.calls.append((embedded_signals, processed_signals))
        return []


async def test_processed_signals_are_joined_to_embeddings_by_id() -> None:
    builder = _GroupBuilder()
    node = GroupSignalsNode(node_logger=_NodeLogger(), signal_group_builder=builder)

    await node.run(
        {
            "processed_signals_by_id": {
                "signal-b": _processed("signal-b"),
                "signal-a": _processed("signal-a"),
            },
            "embedded_signals_by_id": {
                "signal-a": _embedded("signal-a", 1.0),
                "signal-b": _embedded("signal-b", 2.0),
            },
        }
    )

    embedded_signals, processed_signals = builder.calls[0]
    assert [signal.signal_id for signal in processed_signals] == ["signal-b", "signal-a"]
    assert [signal.embedding for signal in embedded_signals] == [[2.0, 0.0], [1.0, 0.0]]


async def test_missing_embedding_is_rejected_before_grouping() -> None:
    builder = _GroupBuilder()
    node = GroupSignalsNode(node_logger=_NodeLogger(), signal_group_builder=builder)

    with pytest.raises(ValueError):
        await node.run(
            {
                "processed_signals_by_id": {
                    "signal-a": _processed("signal-a"),
                },
                "embedded_signals_by_id": {},
            }
        )

    assert builder.calls == []
