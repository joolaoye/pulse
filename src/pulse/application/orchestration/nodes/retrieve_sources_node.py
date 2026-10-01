from typing import Dict, List

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.state import (
    RetrieveSourcesUpdate,
    WorkflowState,
)
from pulse.services.retrieval import XRetriever
from pulse.types import Discourse


class RetrieveSourcesNode(
    BaseNode[
        WorkflowState,
        str,
        List[Discourse],
        RetrieveSourcesUpdate,
    ],
):
    name = "retrieve_sources"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        x_retriever: XRetriever,
        list_id: str,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )

        if not list_id.strip():
            raise ValueError("X list ID cannot be empty.")

        self.x_retriever = x_retriever
        self.list_id = list_id

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> str:
        return self.list_id

    async def _execute(
        self,
        *,
        input_data: str,
    ) -> List[Discourse]:
        return await self.x_retriever.retrieve(
            list_id=input_data,
        )

    def _build_state_update(
        self,
        *,
        output_data: List[Discourse],
    ) -> RetrieveSourcesUpdate:
        return {
            "discourses": output_data,
        }

    def _summarize_input(
        self,
        *,
        input_data: str,
    ) -> Dict[str, object]:
        return {
            "list_id": input_data,
        }

    def _summarize_output(
        self,
        *,
        output_data: List[Discourse],
    ) -> Dict[str, object]:
        return {
            "discourse_count": len(output_data),
        }
