from pulse.agents._base import BaseAgent
from pulse.agents.opening_turn_planning.schemas import (
    OpeningTurnPlanningInput,
    OpeningTurnPlanningOutput,
)
from pulse.agents.opening_turn_planning.system_prompt import SYSTEM_PROMPT
from pulse.agents.opening_turn_planning.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL

OPENING_TURN_PLANNING_MODEL = SONNET_MODEL
OPENING_TURN_PLANNING_TEMPERATURE = 0.4
OPENING_TURN_PLANNING_MAX_TOKENS = 1024


class OpeningTurnPlanningAgent(BaseAgent[OpeningTurnPlanningInput, OpeningTurnPlanningOutput]):
    def __init__(self, llm) -> None:
        super().__init__(llm, OpeningTurnPlanningOutput)

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_user_prompt(
        self,
        input_data: OpeningTurnPlanningInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
