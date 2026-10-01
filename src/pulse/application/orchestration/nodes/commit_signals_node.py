from dataclasses import dataclass
from typing import Dict, List

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import (
    CommitSignalsUpdate,
    WorkflowState,
)
from pulse.services.signals.signal_committer import SignalCommitter
from pulse.types import (
    EmbeddedSignal,
    ProcessedSignal,
    PublicationResult,
    Signal,
    WorkflowOutcome,
)


@dataclass(frozen=True)
class _CommitSignalsNodeInput:
    publication_result: PublicationResult
    signals: List[Signal]
    embedded_signals_by_id: Dict[str, EmbeddedSignal]
    processed_signals_by_id: Dict[str, ProcessedSignal]


class CommitSignalsNode(
    BaseNode[
        WorkflowState,
        _CommitSignalsNodeInput,
        int,
        CommitSignalsUpdate,
    ],
):
    name = "commit_signals"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        signal_committer: SignalCommitter,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )
        self.signal_committer = signal_committer

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> _CommitSignalsNodeInput:
        if "publication_result" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="publication_result",
            )

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

        if "processed_signals_by_id" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="processed_signals_by_id",
            )

        return _CommitSignalsNodeInput(
            publication_result=state["publication_result"],
            signals=state["unseen_signals"],
            embedded_signals_by_id=state["embedded_signals_by_id"],
            processed_signals_by_id=state["processed_signals_by_id"],
        )

    async def _execute(
        self,
        *,
        input_data: _CommitSignalsNodeInput,
    ) -> int:
        await self.signal_committer.commit(
            signals=input_data.signals,
            embedded_signals_by_id=input_data.embedded_signals_by_id,
            processed_signals_by_id=input_data.processed_signals_by_id,
        )

        return len(input_data.processed_signals_by_id)

    def _build_state_update(
        self,
        *,
        output_data: int,
    ) -> CommitSignalsUpdate:
        return {
            "workflow_outcome": WorkflowOutcome.PUBLISHED,
        }

    def _summarize_input(
        self,
        *,
        input_data: _CommitSignalsNodeInput,
    ) -> Dict[str, object]:
        return {
            "signal_count": len(input_data.signals),
            "embedded_signal_count": len(input_data.embedded_signals_by_id),
            "processed_signal_count": len(input_data.processed_signals_by_id),
        }

    def _summarize_output(
        self,
        *,
        output_data: int,
    ) -> Dict[str, object]:
        return {
            "committed_signal_count": output_data,
        }
