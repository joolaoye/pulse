from typing import List

from pulse.agents import (
    QuestionPlanningAgent,
    QuestionPlanningInput,
)
from pulse.types import (
    ConversationAngle,
    ConversationQuestion,
    ConversationQuestions,
    ProcessedSignal,
)


class QuestionPlanner:
    def __init__(
        self,
        *,
        question_planning_agent: QuestionPlanningAgent,
    ) -> None:
        self.question_planning_agent = question_planning_agent

    async def plan(
        self,
        *,
        beat_title: str,
        beat_purpose: str,
        conversation_angle: ConversationAngle,
        topic_signals: List[ProcessedSignal],
        target_duration_seconds: int,
    ) -> ConversationQuestions:
        output = await self.question_planning_agent.arun(
            QuestionPlanningInput(
                beat_title=beat_title,
                beat_purpose=beat_purpose,
                conversation_angle=conversation_angle,
                topic_signals=topic_signals,
                target_duration_seconds=target_duration_seconds,
            )
        )

        return ConversationQuestions(
            questions=[
                ConversationQuestion(
                    question=question.question,
                    rationale=question.rationale,
                )
                for question in output.questions
            ]
        )
