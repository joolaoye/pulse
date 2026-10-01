from typing import Dict, List

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import (
    IngestSignalsUpdate,
    WorkflowState,
)
from pulse.services.ingestion import Ingestor
from pulse.types import Discourse, Signal


class IngestSignalsNode(
    BaseNode[
        WorkflowState,
        List[Discourse],
        List[Signal],
        IngestSignalsUpdate,
    ],
):
    name = "ingest_signals"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        ingestor: Ingestor,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )
        self.ingestor = ingestor

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> List[Discourse]:
        if "discourses" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="discourses",
            )

        return state["discourses"]

    async def _execute(
        self,
        *,
        input_data: List[Discourse],
    ) -> List[Signal]:
        return await self.ingestor.ingest(
            reconstructed_discourses=input_data,
        )

    def _build_state_update(
        self,
        *,
        output_data: List[Signal],
    ) -> IngestSignalsUpdate:
        return {
            "unseen_signals": output_data,
        }

    def _summarize_input(
        self,
        *,
        input_data: List[Discourse],
    ) -> Dict[str, object]:
        return {
            "discourse_count": len(input_data),
        }

    def _summarize_output(
        self,
        *,
        output_data: List[Signal],
    ) -> Dict[str, object]:
        return {
            "unseen_signal_count": len(output_data),
        }
