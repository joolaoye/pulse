from pulse.agents._base import BaseAgent
from pulse.agents.opening_planning.schemas import (
    OpeningPlanningInput,
    OpeningPlanningOutput,
)
from pulse.agents.opening_planning.system_prompt import SYSTEM_PROMPT
from pulse.agents.opening_planning.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL

OPENING_PLANNING_MODEL = SONNET_MODEL
OPENING_PLANNING_TEMPERATURE = 0.3
OPENING_PLANNING_MAX_TOKENS = 1024


class OpeningPlanningAgent(BaseAgent[OpeningPlanningInput, OpeningPlanningOutput]):
    def __init__(self, llm):
        super().__init__(llm, OpeningPlanningOutput)

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_user_prompt(
        self,
        input_data: OpeningPlanningInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
