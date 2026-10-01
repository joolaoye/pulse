from pydantic import ValidationError
import pytest

from pulse.agents.turn_scripting.schemas import TurnScriptingOutput
from pulse.services.scripting.turn_generator import TurnGenerator
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
    EpisodeScript,
    OpeningTurnPlan,
    PodcastProfile,
    ProcessedSignal,
    Segment,
    SegmentTurnPlan,
    SpeakerProfile,
    Turn,
    TurnPlan,
)


def _profile() -> PodcastProfile:
    return PodcastProfile(
        name="Pulse",
        purpose="Explain the week's signals",
        target_audience="Builders",
        editorial_style="Specific",
        conversational_style="Direct",
    )


def _speaker(speaker_id: str) -> SpeakerProfile:
    return SpeakerProfile(
        speaker_id=speaker_id,
        display_name=speaker_id,
        podcast_role=speaker_id,
        persona="Curious",
        speaking_style="Direct",
    )


def _signal(signal_id: str) -> ProcessedSignal:
    return ProcessedSignal(
        signal_id=signal_id,
        title=signal_id,
        markdown_context=signal_id,
        relevance_score=0.8,
        source="x",
    )


def _turn(speaker_id: str, seconds: int) -> Turn:
    return Turn(
        speaker_id=speaker_id,
        conversational_function="explain",
        editorial_objective="Advance the section",
        target_duration_seconds=seconds,
    )


def _beat() -> Beat:
    return Beat(
        primary_signal_id="signal-b",
        supporting_signal_ids=["signal-a"],
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
        target_duration_seconds=270,
    )


def _turn_plan(body_speaker_id: str = "guest", primary_signal_id: str = "signal-b") -> TurnPlan:
    beat = _beat()
    beat.primary_signal_id = primary_signal_id
    segment = Segment(
        title="Segment",
        narrative_goal="Goal",
        target_duration_seconds=270,
        beats=[beat],
    )
    opening = EpisodeOpening(
        target_duration_seconds=15,
        objective="Objective",
        hook_strategy="Hook",
        podcast_introduction_goal="Show",
        speaker_introduction_goal="Speakers",
        listener_promise="Promise",
        transition_goal="Transition",
    )
    closing = EpisodeClosing(
        target_duration_seconds=15,
        objective="Objective",
        resolution_strategy="Resolve",
        final_takeaway="Takeaway",
        closing_goal="Close",
    )
    return TurnPlan(
        opening=OpeningTurnPlan(episode_opening=opening, turns=[_turn("host", 15)]),
        body=BodyTurnPlan(
            body=EpisodeBody(segments=[segment]),
            segment_turn_plans=[
                SegmentTurnPlan(
                    segment=segment,
                    beat_turn_plans=[BeatTurnPlan(beat=beat, turns=[_turn(body_speaker_id, 270)])],
                )
            ],
        ),
        closing=ClosingTurnPlan(episode_closing=closing, turns=[_turn("host", 15)]),
    )


class _ScriptAgent:
    def __init__(self) -> None:
        self.inputs = []

    async def arun(self, *, input_data):
        self.inputs.append(input_data)
        return TurnScriptingOutput(spoken_text=f"line-{len(self.inputs)}")


async def test_script_turns_keep_speaker_order_and_beat_sources() -> None:
    turn_plan = _turn_plan()
    speakers = [_speaker("host"), _speaker("guest")]
    signals = [_signal("signal-a"), _signal("signal-b"), _signal("signal-c")]
    profile = _profile()
    agent = _ScriptAgent()
    beat = turn_plan.body.segment_turn_plans[0].beat_turn_plans[0].beat

    script = await TurnGenerator(turn_scripting_agent=agent).generate(
        turn_plan=turn_plan,
        speakers=speakers,
        signals=signals,
        podcast_profile=profile,
    )

    opening, body, closing = agent.inputs
    assert opening.speaker.speaker_id == "host"
    assert opening.podcast_profile is profile
    assert opening.source_context == []
    assert opening.previous_script_turn is None
    assert opening.planning_context == turn_plan.opening.episode_opening.to_llm_string()
    assert [signal.signal_id for signal in body.source_context] == ["signal-b", "signal-a"]
    assert body.planning_context == beat.to_llm_string()
    assert body.previous_script_turn.spoken_text == "line-1"
    assert closing.source_context == []
    assert closing.planning_context == turn_plan.closing.episode_closing.to_llm_string()
    assert [(turn.speaker_id, turn.spoken_text) for turn in script.turns] == [
        ("host", "line-1"),
        ("guest", "line-2"),
        ("host", "line-3"),
    ]


async def test_script_generation_rejects_an_unknown_speaker() -> None:
    with pytest.raises(ValueError):
        await TurnGenerator(turn_scripting_agent=_ScriptAgent()).generate(
            turn_plan=_turn_plan(body_speaker_id="stranger"),
            speakers=[_speaker("host")],
            signals=[_signal("signal-a"), _signal("signal-b")],
            podcast_profile=_profile(),
        )


async def test_script_generation_rejects_an_unknown_beat_signal() -> None:
    with pytest.raises(ValueError):
        await TurnGenerator(turn_scripting_agent=_ScriptAgent()).generate(
            turn_plan=_turn_plan(primary_signal_id="missing"),
            speakers=[_speaker("host"), _speaker("guest")],
            signals=[_signal("signal-a"), _signal("signal-b")],
            podcast_profile=_profile(),
        )


def test_empty_script_output_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TurnScriptingOutput(spoken_text="")

    with pytest.raises(ValidationError):
        EpisodeScript(turns=[])
