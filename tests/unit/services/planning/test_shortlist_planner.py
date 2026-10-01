import pytest

from pulse.agents.shortlist_planning.schemas import (
    ShortlistPlanningOutput,
    TopicPlanningOutput,
)
from pulse.services.planning.shortlist_planner import ShortlistPlanner
from pulse.types import ProcessedSignal, SegmentOutline


def _signal(signal_id: str) -> ProcessedSignal:
    return ProcessedSignal(
        signal_id=signal_id,
        title=signal_id,
        markdown_context=signal_id,
        relevance_score=0.8,
        source="x",
    )


def _outline() -> SegmentOutline:
    return SegmentOutline(
        cluster_id=1,
        title="Segment",
        narrative_goal="Develop the cluster",
        target_duration_seconds=30,
    )


class _ShortlistAgent:
    def __init__(self, output: ShortlistPlanningOutput) -> None:
        self.output = output
        self.inputs = []

    async def arun(self, planning_input):
        self.inputs.append(planning_input)
        return self.output


async def test_shortlist_preserves_topic_signal_references_and_order() -> None:
    signals = [_signal("signal-a"), _signal("signal-b")]
    outline = _outline()
    agent = _ShortlistAgent(
        ShortlistPlanningOutput(
            topics=[
                TopicPlanningOutput(
                    primary_signal_id="signal-b",
                    supporting_signal_ids=["signal-a"],
                    editorial_goal="Lead with the second signal",
                    duration_weight=2,
                ),
                TopicPlanningOutput(
                    primary_signal_id="signal-a",
                    supporting_signal_ids=[],
                    editorial_goal="Return to the first signal",
                    duration_weight=1,
                ),
            ]
        )
    )

    shortlist = await ShortlistPlanner(shortlist_planning_agent=agent).plan(
        segment_outline=outline,
        relevant_signals=signals,
    )

    assert agent.inputs[0].segment_outline is outline
    assert agent.inputs[0].relevant_signals == signals
    assert [
        (topic.primary_signal_id, topic.supporting_signal_ids, topic.duration_weight)
        for topic in shortlist.topics
    ] == [
        ("signal-b", ["signal-a"], 2),
        ("signal-a", [], 1),
    ]


async def test_shortlist_rejects_a_primary_signal_used_as_its_own_support() -> None:
    agent = _ShortlistAgent(
        ShortlistPlanningOutput(
            topics=[
                TopicPlanningOutput(
                    primary_signal_id="signal-a",
                    supporting_signal_ids=["signal-a"],
                    editorial_goal="Conflict",
                    duration_weight=1,
                )
            ]
        )
    )

    with pytest.raises(ValueError):
        await ShortlistPlanner(shortlist_planning_agent=agent).plan(
            segment_outline=_outline(),
            relevant_signals=[_signal("signal-a")],
        )
