from dataclasses import dataclass
from typing import Dict, List

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import (
    PostProcessSignalsUpdate,
    WorkflowState,
)
from pulse.services.signals import PostProcessor
from pulse.types import (
    EmbeddedSignal,
    ProcessedSignal,
    Signal,
)


@dataclass(frozen=True)
class _PostProcessSignalsNodeInput:
    signals: List[Signal]
    embedded_signals: List[EmbeddedSignal]


class PostProcessSignalsNode(
    BaseNode[
        WorkflowState,
        _PostProcessSignalsNodeInput,
        List[ProcessedSignal],
        PostProcessSignalsUpdate,
    ],
):
    name = "post_process_signals"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        post_processor: PostProcessor,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )
        self.post_processor = post_processor

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> _PostProcessSignalsNodeInput:
        if "unseen_signals" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="unseen_signals",
            )

        if "embedded_signals_by_id" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="embedded_signals_by_id",
            )

        return _PostProcessSignalsNodeInput(
            signals=state["unseen_signals"],
            embedded_signals=list(state["embedded_signals_by_id"].values()),
        )

    async def _execute(
        self,
        *,
        input_data: _PostProcessSignalsNodeInput,
    ) -> List[ProcessedSignal]:
        return await self.post_processor.process(
            signals=input_data.signals,
            embedded_signals=input_data.embedded_signals,
        )

    def _build_state_update(
        self,
        *,
        output_data: List[ProcessedSignal],
    ) -> PostProcessSignalsUpdate:
        return {
            "processed_signals_by_id": {signal.signal_id: signal for signal in output_data},
        }

    def _summarize_input(
        self,
        *,
        input_data: _PostProcessSignalsNodeInput,
    ) -> Dict[str, object]:
        return {
            "signal_count": len(input_data.signals),
            "embedded_signal_count": len(input_data.embedded_signals),
        }

    def _summarize_output(
        self,
        *,
        output_data: List[ProcessedSignal],
    ) -> Dict[str, object]:
        return {
            "processed_signal_count": len(output_data),
        }
