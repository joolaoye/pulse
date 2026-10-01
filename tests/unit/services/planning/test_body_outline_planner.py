import pytest

from pulse.agents.body_outline_planning.schemas import (
    BodyOutlinePlanningOutput,
    SegmentOutlinePlanningOutput,
)
from pulse.services.planning.body_outline_planner import BodyOutlinePlanner
from pulse.types import ProcessedSignal, Theme, ThemedSignalCluster


def _signal(signal_id: str) -> ProcessedSignal:
    return ProcessedSignal(
        signal_id=signal_id,
        title=signal_id,
        markdown_context=signal_id,
        relevance_score=0.8,
        source="x",
    )


def _cluster(cluster_id: int, signal_ids: list[str]) -> ThemedSignalCluster:
    return ThemedSignalCluster(
        cluster_id=cluster_id,
        relevance_score=0.5 + cluster_id,
        theme=Theme(title=f"Theme {cluster_id}", summary="Summary"),
        signal_ids=signal_ids,
    )


class _OutlineAgent:
    def __init__(self, output: BodyOutlinePlanningOutput) -> None:
        self.output = output
        self.inputs = []

    async def arun(self, planning_input):
        self.inputs.append(planning_input)
        return self.output


async def test_body_outline_keeps_cluster_identity_and_allocates_duration() -> None:
    first = _cluster(7, ["signal-b", "signal-a"])
    second = _cluster(2, ["signal-c"])
    signals = [_signal("signal-a"), _signal("signal-b"), _signal("signal-c")]
    agent = _OutlineAgent(
        BodyOutlinePlanningOutput(
            segments=[
                SegmentOutlinePlanningOutput(
                    cluster_id=2,
                    title="Later",
                    narrative_goal="Close the body",
                    duration_weight=1,
                ),
                SegmentOutlinePlanningOutput(
                    cluster_id=7,
                    title="Earlier",
                    narrative_goal="Open the body",
                    duration_weight=3,
                ),
            ]
        )
    )

    outline = await BodyOutlinePlanner(body_outline_planning_agent=agent).plan(
        themed_signal_clusters=[first, second],
        processed_signals=signals,
        target_body_duration_seconds=10,
    )

    planning_input = agent.inputs[0]
    assert planning_input.target_body_duration_seconds == 10
    assert [cluster.cluster_id for cluster in planning_input.candidate_clusters] == [7, 2]
    assert [signal.signal_id for signal in planning_input.candidate_clusters[0].signals] == [
        "signal-b",
        "signal-a",
    ]
    assert [signal.signal_id for signal in planning_input.candidate_clusters[1].signals] == [
        "signal-c"
    ]
    assert [
        (segment.cluster_id, segment.target_duration_seconds) for segment in outline.segments
    ] == [
        (2, 3),
        (7, 7),
    ]
    assert [segment.title for segment in outline.segments] == ["Later", "Earlier"]


async def test_body_outline_rejects_an_unknown_cluster() -> None:
    agent = _OutlineAgent(
        BodyOutlinePlanningOutput(
            segments=[
                SegmentOutlinePlanningOutput(
                    cluster_id=99,
                    title="Missing",
                    narrative_goal="Missing",
                    duration_weight=1,
                )
            ]
        )
    )

    with pytest.raises(ValueError):
        await BodyOutlinePlanner(body_outline_planning_agent=agent).plan(
            themed_signal_clusters=[_cluster(7, ["signal-a"])],
            processed_signals=[_signal("signal-a")],
            target_body_duration_seconds=10,
        )
