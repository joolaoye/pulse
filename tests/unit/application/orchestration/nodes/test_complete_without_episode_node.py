import pytest

from pulse.application.orchestration.nodes.complete_without_episode_node import (
    CompleteWithoutEpisodeNode,
)
from pulse.types import NoContentReason, WorkflowOutcome


class _NodeLogger:
    def node_started(self, **kwargs) -> None:
        del kwargs

    def node_completed(self, **kwargs) -> None:
        del kwargs

    def node_failed(self, **kwargs) -> None:
        del kwargs


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        (
            {"unseen_signals": []},
            NoContentReason.NO_UNSEEN_SIGNALS,
        ),
        (
            {
                "unseen_signals": ["signal-a"],
                "embedded_signals_by_id": {},
            },
            NoContentReason.NO_SEMANTICALLY_UNIQUE_SIGNALS,
        ),
        (
            {
                "unseen_signals": ["signal-a"],
                "embedded_signals_by_id": {"signal-a": object()},
                "processed_signals_by_id": {},
            },
            NoContentReason.NO_PROCESSED_SIGNALS,
        ),
        (
            {
                "unseen_signals": ["signal-a"],
                "embedded_signals_by_id": {"signal-a": object()},
                "processed_signals_by_id": {"signal-a": object()},
            },
            NoContentReason.NO_THEMED_CLUSTERS,
        ),
    ],
)
async def test_no_content_reason_follows_the_first_empty_stage(
    state: dict,
    reason: NoContentReason,
) -> None:
    update = await CompleteWithoutEpisodeNode(node_logger=_NodeLogger()).run(state)

    assert update["no_content_reason"] == reason
    assert update["workflow_outcome"] == WorkflowOutcome.NO_CONTENT
