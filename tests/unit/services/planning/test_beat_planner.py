import pytest

from pulse.agents.beat_planning.schemas import BeatPlanningOutput
from pulse.services.planning.beat_planner import BeatPlanner
from pulse.types import (
    Beat,
    ConversationAngle,
    ConversationQuestion,
    ConversationQuestions,
    ProcessedSignal,
    Topic,
)


def _signal(signal_id: str) -> ProcessedSignal:
    return ProcessedSignal(
        signal_id=signal_id,
        title=signal_id,
        markdown_context=signal_id,
        relevance_score=0.8,
        source="x",
    )


def _angle() -> ConversationAngle:
    return ConversationAngle(
        title="Angle",
        perspective="Developer",
        central_thesis="Thesis",
        narrative_hook="Hook",
        listener_value="Value",
        tension="Tension",
    )


def _questions() -> ConversationQuestions:
    return ConversationQuestions(
        questions=[ConversationQuestion(question="Why?", rationale="It advances the beat")]
    )


def _previous_beat() -> Beat:
    return Beat(
        primary_signal_id="signal-earlier",
        title="Earlier",
        purpose="Set up the next beat",
        conversation_angle=_angle(),
        questions=_questions(),
        target_duration_seconds=10,
    )


class _BeatAgent:
    def __init__(self, output: BeatPlanningOutput) -> None:
        self.output = output
        self.inputs = []

    async def arun(self, planning_input):
        self.inputs.append(planning_input)
        return self.output


class _AnglePlanner:
    def __init__(self, angle: ConversationAngle) -> None:
        self.angle = angle
        self.calls = []

    async def plan(self, *, beat_title: str, beat_purpose: str, topic_signals):
        self.calls.append((beat_title, beat_purpose, topic_signals))
        return self.angle


class _QuestionPlanner:
    def __init__(self, questions: ConversationQuestions) -> None:
        self.questions = questions
        self.calls = []

    async def plan(
        self,
        *,
        beat_title: str,
        beat_purpose: str,
        conversation_angle: ConversationAngle,
        topic_signals,
        target_duration_seconds: int,
    ):
        self.calls.append(
            (beat_title, beat_purpose, conversation_angle, topic_signals, target_duration_seconds)
        )
        return self.questions


async def test_beat_inherits_topic_signals_and_requested_duration() -> None:
    topic = Topic(
        primary_signal_id="signal-b",
        supporting_signal_ids=["signal-a"],
        editorial_goal="Connect the two signals",
        duration_weight=2,
    )
    signals = [_signal("signal-a"), _signal("signal-b"), _signal("signal-c")]
    angle = _angle()
    questions = _questions()
    agent = _BeatAgent(
        BeatPlanningOutput(
            title="The connection",
            purpose="Show how the signals relate",
            segue_transition="Move from the earlier beat",
        )
    )
    angle_planner = _AnglePlanner(angle)
    question_planner = _QuestionPlanner(questions)

    beat = await BeatPlanner(
        beat_planning_agent=agent,
        conversation_angle_planner=angle_planner,
        question_planner=question_planner,
    ).plan(
        topic=topic,
        relevant_signals=signals,
        target_duration_seconds=12,
        previous_beat=_previous_beat(),
    )

    planning_input = agent.inputs[0]
    assert planning_input.topic is topic
    assert [signal.signal_id for signal in planning_input.topic_signals] == [
        "signal-b",
        "signal-a",
    ]
    assert planning_input.target_duration_seconds == 12
    assert planning_input.previous_beat_context.title == "Earlier"
    assert planning_input.previous_beat_context.purpose == "Set up the next beat"
    assert angle_planner.calls[0][0:2] == ("The connection", "Show how the signals relate")
    assert [signal.signal_id for signal in angle_planner.calls[0][2]] == ["signal-b", "signal-a"]
    assert question_planner.calls[0][2] is angle
    assert question_planner.calls[0][4] == 12
    assert beat.primary_signal_id == "signal-b"
    assert beat.supporting_signal_ids == ["signal-a"]
    assert beat.conversation_angle is angle
    assert beat.questions is questions
    assert beat.segue_transition == "Move from the earlier beat"
    assert beat.target_duration_seconds == 12


async def test_beat_rejects_an_unknown_signal_reference() -> None:
    beat_planning_agent = _BeatAgent(BeatPlanningOutput(title="Title", purpose="Purpose"))
    planner = BeatPlanner(
        beat_planning_agent=beat_planning_agent,
        conversation_angle_planner=_AnglePlanner(_angle()),
        question_planner=_QuestionPlanner(_questions()),
    )

    with pytest.raises(ValueError):
        await planner.plan(
            topic=Topic(
                primary_signal_id="missing",
                editorial_goal="Missing",
                duration_weight=1,
            ),
            relevant_signals=[_signal("signal-a")],
            target_duration_seconds=10,
        )

    assert beat_planning_agent.inputs == []


async def test_first_beat_rejects_a_segue() -> None:
    planner = BeatPlanner(
        beat_planning_agent=_BeatAgent(
            BeatPlanningOutput(
                title="Title",
                purpose="Purpose",
                segue_transition="There is no previous beat",
            )
        ),
        conversation_angle_planner=_AnglePlanner(_angle()),
        question_planner=_QuestionPlanner(_questions()),
    )

    with pytest.raises(ValueError):
        await planner.plan(
            topic=Topic(
                primary_signal_id="signal-a",
                editorial_goal="Open",
                duration_weight=1,
            ),
            relevant_signals=[_signal("signal-a")],
            target_duration_seconds=10,
        )
