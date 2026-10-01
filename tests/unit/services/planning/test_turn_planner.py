import pytest

from pulse.services.planning.turn_planner import TurnPlanner
from pulse.types import (
    Beat,
    BeatTurnPlan,
    BodyTurnPlan,
    ClosingTurnPlan,
    ConversationAngle,
    ConversationQuestion,
    ConversationQuestions,
    EpisodeBody,
    EpisodeClosing,
    EpisodeOpening,
    EpisodePlan,
    OpeningTurnPlan,
    Segment,
    SegmentTurnPlan,
    SpeakerProfile,
    Turn,
)


def _speakers() -> list[SpeakerProfile]:
    return [
        SpeakerProfile(
            speaker_id="host",
            display_name="Host",
            podcast_role="Host",
            persona="Curious",
            speaking_style="Direct",
        )
    ]


def _beat(signal_id: str, duration_seconds: int) -> Beat:
    return Beat(
        primary_signal_id=signal_id,
        title=signal_id,
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
        target_duration_seconds=duration_seconds,
    )


def _segment(title: str, signal_id: str, duration_seconds: int) -> Segment:
    return Segment(
        title=title,
        narrative_goal=title,
        target_duration_seconds=duration_seconds,
        beats=[_beat(signal_id, duration_seconds)],
    )


def _episode_plan() -> EpisodePlan:
    return EpisodePlan(
        opening=EpisodeOpening(
            target_duration_seconds=15,
            objective="Objective",
            hook_strategy="Hook",
            podcast_introduction_goal="Show",
            speaker_introduction_goal="Speakers",
            listener_promise="Promise",
            transition_goal="Transition",
        ),
        body=EpisodeBody(
            segments=[
                _segment("First", "signal-a", 150),
                _segment("Last", "signal-b", 120),
            ]
        ),
        closing=EpisodeClosing(
            target_duration_seconds=15,
            objective="Objective",
            resolution_strategy="Resolve",
            final_takeaway="Takeaway",
            closing_goal="Close",
        ),
    )


def _turn(seconds: int) -> Turn:
    return Turn(
        speaker_id="host",
        conversational_function="explain",
        editorial_objective="Advance the section",
        target_duration_seconds=seconds,
    )


class _OpeningTurnPlanner:
    def __init__(self, seconds: int) -> None:
        self.seconds = seconds
        self.calls = []

    async def plan(self, *, episode_opening, first_segment, speakers):
        self.calls.append((episode_opening, first_segment, speakers))
        return OpeningTurnPlan(episode_opening=episode_opening, turns=[_turn(self.seconds)])


class _BodyTurnPlanner:
    def __init__(self, episode_plan: EpisodePlan) -> None:
        self.episode_plan = episode_plan
        self.calls = []

    async def plan(self, *, episode_body, speakers):
        self.calls.append((episode_body, speakers))
        return BodyTurnPlan(
            body=episode_body,
            segment_turn_plans=[
                SegmentTurnPlan(
                    segment=segment,
                    beat_turn_plans=[
                        BeatTurnPlan(
                            beat=segment.beats[0],
                            turns=[_turn(segment.target_duration_seconds)],
                        )
                    ],
                )
                for segment in episode_body.segments
            ],
        )


class _ClosingTurnPlanner:
    def __init__(self) -> None:
        self.calls = []

    async def plan(self, *, episode_closing, final_segment, speakers):
        self.calls.append((episode_closing, final_segment, speakers))
        return ClosingTurnPlan(episode_closing=episode_closing, turns=[_turn(15)])


async def test_turn_plan_keeps_section_context_and_total_duration() -> None:
    episode_plan = _episode_plan()
    speakers = _speakers()
    opening_planner = _OpeningTurnPlanner(15)
    body_planner = _BodyTurnPlanner(episode_plan)
    closing_planner = _ClosingTurnPlanner()

    turn_plan = await TurnPlanner(
        opening_turn_planner=opening_planner,
        body_turn_planner=body_planner,
        closing_turn_planner=closing_planner,
    ).plan(episode_plan=episode_plan, speakers=speakers)

    assert opening_planner.calls == [
        (episode_plan.opening, episode_plan.body.segments[0], speakers)
    ]
    assert body_planner.calls == [(episode_plan.body, speakers)]
    assert closing_planner.calls == [
        (episode_plan.closing, episode_plan.body.segments[-1], speakers)
    ]
    assert turn_plan.total_duration_seconds == episode_plan.total_duration_seconds
    assert [segment.segment.title for segment in turn_plan.body.segment_turn_plans] == [
        "First",
        "Last",
    ]


async def test_turn_plan_rejects_a_duration_mismatch() -> None:
    episode_plan = _episode_plan()

    with pytest.raises(ValueError):
        await TurnPlanner(
            opening_turn_planner=_OpeningTurnPlanner(14),
            body_turn_planner=_BodyTurnPlanner(episode_plan),
            closing_turn_planner=_ClosingTurnPlanner(),
        ).plan(episode_plan=episode_plan, speakers=_speakers())
