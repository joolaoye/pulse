from typing import Dict, List

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import (
    ProcessSemanticsUpdate,
    WorkflowState,
)
from pulse.services.signals import SemanticProcessor
from pulse.types import EmbeddedSignal, Signal


class ProcessSemanticsNode(
    BaseNode[
        WorkflowState,
        List[Signal],
        List[EmbeddedSignal],
        ProcessSemanticsUpdate,
    ],
):
    name = "process_semantics"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        semantic_processor: SemanticProcessor,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )
        self.semantic_processor = semantic_processor

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> List[Signal]:
        if "unseen_signals" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="unseen_signals",
            )

        return state["unseen_signals"]

    async def _execute(
        self,
        *,
        input_data: List[Signal],
    ) -> List[EmbeddedSignal]:
        return await self.semantic_processor.process(
            signals=input_data,
        )

    def _build_state_update(
        self,
        *,
        output_data: List[EmbeddedSignal],
    ) -> ProcessSemanticsUpdate:
        return {
            "embedded_signals_by_id": {signal.signal_id: signal for signal in output_data},
        }

    def _summarize_input(
        self,
        *,
        input_data: List[Signal],
    ) -> Dict[str, object]:
        return {
            "unseen_signal_count": len(input_data),
        }

    def _summarize_output(
        self,
        *,
        output_data: List[EmbeddedSignal],
    ) -> Dict[str, object]:
        return {
            "embedded_signal_count": len(output_data),
        }
