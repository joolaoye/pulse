from typing import List, Optional

from pulse.agents import (
    BeatPlanningAgent,
    BeatPlanningInput,
    PreviousBeatContext,
)
from pulse.services.planning.conversation_angle_planner import ConversationAnglePlanner
from pulse.services.planning.question_planner import QuestionPlanner
from pulse.types import (
    Beat,
    ProcessedSignal,
    Topic,
)


class BeatPlanner:
    def __init__(
        self,
        *,
        beat_planning_agent: BeatPlanningAgent,
        conversation_angle_planner: ConversationAnglePlanner,
        question_planner: QuestionPlanner,
    ) -> None:
        self.beat_planning_agent = beat_planning_agent
        self.conversation_angle_planner = conversation_angle_planner
        self.question_planner = question_planner

    async def plan(
        self,
        *,
        topic: Topic,
        relevant_signals: List[ProcessedSignal],
        target_duration_seconds: int,
        previous_beat: Optional[Beat] = None,
    ) -> Beat:
        topic_signals = self._resolve_topic_signals(
            topic=topic,
            relevant_signals=relevant_signals,
        )

        output = await self.beat_planning_agent.arun(
            BeatPlanningInput(
                topic=topic,
                topic_signals=topic_signals,
                target_duration_seconds=target_duration_seconds,
                previous_beat_context=self._build_previous_beat_context(
                    previous_beat=previous_beat,
                ),
            )
        )

        self._validate_segue_transition(
            previous_beat=previous_beat,
            segue_transition=output.segue_transition,
        )

        conversation_angle = await self.conversation_angle_planner.plan(
            beat_title=output.title,
            beat_purpose=output.purpose,
            topic_signals=topic_signals,
        )

        questions = await self.question_planner.plan(
            beat_title=output.title,
            beat_purpose=output.purpose,
            conversation_angle=conversation_angle,
            topic_signals=topic_signals,
            target_duration_seconds=target_duration_seconds,
        )

        return Beat(
            primary_signal_id=topic.primary_signal_id,
            supporting_signal_ids=topic.supporting_signal_ids,
            title=output.title,
            purpose=output.purpose,
            conversation_angle=conversation_angle,
            questions=questions,
            segue_transition=output.segue_transition,
            target_duration_seconds=target_duration_seconds,
        )

    @staticmethod
    def _resolve_topic_signals(
        *,
        topic: Topic,
        relevant_signals: List[ProcessedSignal],
    ) -> List[ProcessedSignal]:
        signal_ids = [signal.signal_id for signal in relevant_signals]

        if len(signal_ids) != len(set(signal_ids)):
            raise ValueError("Relevant signals contain duplicate signal IDs.")

        signals_by_id = {signal.signal_id: signal for signal in relevant_signals}

        topic_signal_ids = [
            topic.primary_signal_id,
            *topic.supporting_signal_ids,
        ]

        unknown_signal_ids = [
            signal_id for signal_id in topic_signal_ids if signal_id not in signals_by_id
        ]

        if unknown_signal_ids:
            raise ValueError(f"Topic references unknown signal IDs: {unknown_signal_ids}.")

        return [signals_by_id[signal_id] for signal_id in topic_signal_ids]

    @staticmethod
    def _build_previous_beat_context(
        *,
        previous_beat: Optional[Beat],
    ) -> Optional[PreviousBeatContext]:
        if previous_beat is None:
            return None

        return PreviousBeatContext(
            title=previous_beat.title,
            purpose=previous_beat.purpose,
        )

    @staticmethod
    def _validate_segue_transition(
        *,
        previous_beat: Optional[Beat],
        segue_transition: Optional[str],
    ) -> None:
        if previous_beat is None:
            if segue_transition is not None:
                raise ValueError(
                    "Beat planning output contains a segue transition when no previous beat exists."
                )
            return

        if segue_transition is None or not segue_transition.strip():
            raise ValueError(
                "Beat planning output must contain a segue transition when a previous beat exists."
            )
