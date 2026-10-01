from pulse.agents._shared.turn_planning import TurnPlanningOutputItem
from pulse.agents.body_turn_planning.schemas import BodyTurnPlanningOutput
from pulse.services.planning.body_turn_planner import BodyTurnPlanner
from pulse.types import (
    Beat,
    ConversationAngle,
    ConversationQuestion,
    ConversationQuestions,
    EpisodeBody,
    Segment,
    SpeakerProfile,
)


def _speakers() -> list[SpeakerProfile]:
    return [
        SpeakerProfile(
            speaker_id="host",
            display_name="Host",
            podcast_role="Host",
            persona="Curious",
            speaking_style="Direct",
        ),
        SpeakerProfile(
            speaker_id="guest",
            display_name="Guest",
            podcast_role="Guest",
            persona="Specific",
            speaking_style="Concrete",
        ),
    ]


def _beat() -> Beat:
    return Beat(
        primary_signal_id="signal-a",
        supporting_signal_ids=["signal-b"],
        title="Beat",
        purpose="Purpose",
        conversation_angle=ConversationAngle(
            title="Angle",
            perspective="Developer",
            central_thesis="Thesis",
            narrative_hook="Hook",
            listener_value="Value",
            tension="Tension",
        ),
        questions=ConversationQuestions(
            questions=[ConversationQuestion(question="Why?", rationale="Because")]
        ),
        target_duration_seconds=10,
    )


class _TurnAgent:
    def __init__(self, output: BodyTurnPlanningOutput) -> None:
        self.output = output
        self.inputs = []

    async def arun(self, planning_input):
        self.inputs.append(planning_input)
        return self.output


async def test_body_turns_keep_speaker_order_beat_and_allocated_duration() -> None:
    beat = _beat()
    speakers = _speakers()
    body = EpisodeBody(
        segments=[
            Segment(
                title="Segment",
                narrative_goal="Goal",
                target_duration_seconds=10,
                beats=[beat],
            )
        ]
    )
    agent = _TurnAgent(
        BodyTurnPlanningOutput(
            turns=[
                TurnPlanningOutputItem(
                    speaker_id="guest",
                    conversational_function="challenge",
                    editorial_objective="Question the claim",
                    duration_weight=1,
                ),
                TurnPlanningOutputItem(
                    speaker_id="host",
                    conversational_function="explain",
                    editorial_objective="Ground the answer",
                    duration_weight=2,
                ),
            ]
        )
    )

    plan = await BodyTurnPlanner(body_turn_planning_agent=agent).plan(
        episode_body=body,
        speakers=speakers,
    )

    assert agent.inputs[0].beat is beat
    assert agent.inputs[0].speakers == speakers
    beat_plan = plan.segment_turn_plans[0].beat_turn_plans[0]
    assert beat_plan.beat is beat
    assert [
        (turn.speaker_id, turn.conversational_function, turn.target_duration_seconds)
        for turn in beat_plan.turns
    ] == [
        ("guest", "challenge", 3),
        ("host", "explain", 7),
    ]
