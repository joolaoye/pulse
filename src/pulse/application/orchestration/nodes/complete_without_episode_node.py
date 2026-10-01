from typing import ClassVar

from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.state import (
    CompleteWithoutEpisodeUpdate,
    WorkflowState,
)
from pulse.types import (
    NoContentReason,
    WorkflowOutcome,
)


class CompleteWithoutEpisodeNode(
    BaseNode[
        WorkflowState,
        NoContentReason,
        NoContentReason,
        CompleteWithoutEpisodeUpdate,
    ],
):
    name: ClassVar[str] = "complete_without_episode"

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> NoContentReason:
        if not state.get("unseen_signals"):
            return NoContentReason.NO_UNSEEN_SIGNALS

        if not state.get("embedded_signals_by_id"):
            return NoContentReason.NO_SEMANTICALLY_UNIQUE_SIGNALS

        if not state.get("processed_signals_by_id"):
            return NoContentReason.NO_PROCESSED_SIGNALS

        return NoContentReason.NO_THEMED_CLUSTERS

    async def _execute(
        self,
        *,
        input_data: NoContentReason,
    ) -> NoContentReason:
        return input_data

    def _build_state_update(
        self,
        *,
        output_data: NoContentReason,
    ) -> CompleteWithoutEpisodeUpdate:
        return CompleteWithoutEpisodeUpdate(
            workflow_outcome=WorkflowOutcome.NO_CONTENT,
            no_content_reason=output_data,
        )
