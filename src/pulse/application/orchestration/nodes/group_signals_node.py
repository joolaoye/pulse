from dataclasses import dataclass
from typing import Dict, List

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import (
    GroupSignalsUpdate,
    WorkflowState,
)
from pulse.services.grouping import SignalGroupBuilder
from pulse.types import (
    EmbeddedSignal,
    ProcessedSignal,
    ThemedSignalCluster,
)


@dataclass(frozen=True)
class _GroupSignalsNodeInput:
    embedded_signals: List[EmbeddedSignal]
    processed_signals: List[ProcessedSignal]


class GroupSignalsNode(
    BaseNode[
        WorkflowState,
        _GroupSignalsNodeInput,
        List[ThemedSignalCluster],
        GroupSignalsUpdate,
    ],
):
    name = "group_signals"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        signal_group_builder: SignalGroupBuilder,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )
        self.signal_group_builder = signal_group_builder

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> _GroupSignalsNodeInput:
        if "embedded_signals_by_id" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="embedded_signals_by_id",
            )

        if "processed_signals_by_id" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="processed_signals_by_id",
            )

        embedded_signals_by_id = state["embedded_signals_by_id"]
        processed_signals_by_id = state["processed_signals_by_id"]

        embedded_signals: List[EmbeddedSignal] = []
        processed_signals: List[ProcessedSignal] = []

        for signal_id, processed_signal in processed_signals_by_id.items():
            embedded_signal = embedded_signals_by_id.get(signal_id)

            if embedded_signal is None:
                raise ValueError(
                    "GroupSignalsNode cannot group a processed signal "
                    "without its corresponding embedding. "
                    f"Signal ID: {signal_id}."
                )

            processed_signals.append(processed_signal)
            embedded_signals.append(embedded_signal)

        return _GroupSignalsNodeInput(
            embedded_signals=embedded_signals,
            processed_signals=processed_signals,
        )

    async def _execute(
        self,
        *,
        input_data: _GroupSignalsNodeInput,
    ) -> List[ThemedSignalCluster]:
        return await self.signal_group_builder.build(
            embedded_signals=input_data.embedded_signals,
            processed_signals=input_data.processed_signals,
        )

    def _build_state_update(
        self,
        *,
        output_data: List[ThemedSignalCluster],
    ) -> GroupSignalsUpdate:
        return {
            "themed_signal_clusters": output_data,
        }

    def _summarize_input(
        self,
        *,
        input_data: _GroupSignalsNodeInput,
    ) -> Dict[str, object]:
        return {
            "embedded_signal_count": len(input_data.embedded_signals),
            "processed_signal_count": len(input_data.processed_signals),
        }

    def _summarize_output(
        self,
        *,
        output_data: List[ThemedSignalCluster],
    ) -> Dict[str, object]:
        return {
            "themed_signal_cluster_count": len(output_data),
        }
