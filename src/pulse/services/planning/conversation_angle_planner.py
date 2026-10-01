from typing import List

from pulse.agents import (
    ConversationAnglePlanningAgent,
    ConversationAnglePlanningInput,
)
from pulse.types import (
    ConversationAngle,
    ProcessedSignal,
)


class ConversationAnglePlanner:
    def __init__(
        self,
        *,
        conversation_angle_planning_agent: ConversationAnglePlanningAgent,
    ) -> None:
        self.conversation_angle_planning_agent = conversation_angle_planning_agent

    async def plan(
        self,
        *,
        beat_title: str,
        beat_purpose: str,
        topic_signals: List[ProcessedSignal],
    ) -> ConversationAngle:
        output = await self.conversation_angle_planning_agent.arun(
            ConversationAnglePlanningInput(
                beat_title=beat_title,
                beat_purpose=beat_purpose,
                topic_signals=topic_signals,
            )
        )

        return ConversationAngle(
            title=output.title,
            perspective=output.perspective,
            central_thesis=output.central_thesis,
            narrative_hook=output.narrative_hook,
            listener_value=output.listener_value,
            tension=output.tension,
        )
