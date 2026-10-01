from pulse.agents._base import BaseAgent
from pulse.agents.closing_planning.schemas import (
    ClosingPlanningInput,
    ClosingPlanningOutput,
)
from pulse.agents.closing_planning.system_prompt import SYSTEM_PROMPT
from pulse.agents.closing_planning.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL

CLOSING_PLANNING_MODEL = SONNET_MODEL
CLOSING_PLANNING_TEMPERATURE = 0.3
CLOSING_PLANNING_MAX_TOKENS = 1024


class ClosingPlanningAgent(BaseAgent[ClosingPlanningInput, ClosingPlanningOutput]):
    def __init__(self, llm):
        super().__init__(llm, ClosingPlanningOutput)

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_user_prompt(
        self,
        input_data: ClosingPlanningInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
