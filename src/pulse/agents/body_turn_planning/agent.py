from pulse.agents._base import BaseAgent
from pulse.agents.body_turn_planning.schemas import (
    BodyTurnPlanningInput,
    BodyTurnPlanningOutput,
)
from pulse.agents.body_turn_planning.system_prompt import SYSTEM_PROMPT
from pulse.agents.body_turn_planning.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL

BODY_TURN_PLANNING_MODEL = SONNET_MODEL
BODY_TURN_PLANNING_TEMPERATURE = 0.2
BODY_TURN_PLANNING_MAX_TOKENS = 2048


class BodyTurnPlanningAgent(BaseAgent[BodyTurnPlanningInput, BodyTurnPlanningOutput]):
    def __init__(self, llm) -> None:
        super().__init__(llm, BodyTurnPlanningOutput)

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_user_prompt(
        self,
        input_data: BodyTurnPlanningInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
