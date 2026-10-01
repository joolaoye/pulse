from pulse.agents._base import BaseAgent
from pulse.agents.shortlist_planning.examples import EXAMPLES
from pulse.agents.shortlist_planning.schemas import (
    ShortlistPlanningInput,
    ShortlistPlanningOutput,
)
from pulse.agents.shortlist_planning.system_prompt import SYSTEM_PROMPT
from pulse.agents.shortlist_planning.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL
from pulse.infrastructure.prompting import PromptBuilder

SHORTLIST_PLANNING_MODEL = SONNET_MODEL
SHORTLIST_PLANNING_TEMPERATURE = 0.0
SHORTLIST_PLANNING_MAX_TOKENS = 2048


class ShortlistPlanningAgent(BaseAgent[ShortlistPlanningInput, ShortlistPlanningOutput]):
    def __init__(self, llm):
        super().__init__(llm, ShortlistPlanningOutput)

    def build_system_prompt(self) -> str:
        return PromptBuilder.inject_examples(
            SYSTEM_PROMPT,
            PromptBuilder.render_examples(EXAMPLES),
        )

    def build_user_prompt(
        self,
        input_data: ShortlistPlanningInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
