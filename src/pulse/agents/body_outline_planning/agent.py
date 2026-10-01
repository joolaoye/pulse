from pulse.agents._base import BaseAgent
from pulse.agents.body_outline_planning.schemas import (
    BodyOutlinePlanningInput,
    BodyOutlinePlanningOutput,
)
from pulse.agents.body_outline_planning.system_prompt import SYSTEM_PROMPT
from pulse.agents.body_outline_planning.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL

BODY_OUTLINE_PLANNING_MODEL = SONNET_MODEL
BODY_OUTLINE_PLANNING_TEMPERATURE = 0.2
BODY_OUTLINE_PLANNING_MAX_TOKENS = 2048


class BodyOutlinePlanningAgent(BaseAgent[BodyOutlinePlanningInput, BodyOutlinePlanningOutput]):
    def __init__(self, llm):
        super().__init__(llm, BodyOutlinePlanningOutput)

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_user_prompt(
        self,
        input_data: BodyOutlinePlanningInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
