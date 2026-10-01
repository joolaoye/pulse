from pulse.agents._base import BaseAgent
from pulse.agents.question_planning.examples import EXAMPLES
from pulse.agents.question_planning.schemas import (
    QuestionPlanningInput,
    QuestionPlanningOutput,
)
from pulse.agents.question_planning.system_prompt import SYSTEM_PROMPT
from pulse.agents.question_planning.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL
from pulse.infrastructure.prompting import PromptBuilder

QUESTION_PLANNING_MODEL = SONNET_MODEL
QUESTION_PLANNING_TEMPERATURE = 0.6
QUESTION_PLANNING_MAX_TOKENS = 1024


class QuestionPlanningAgent(BaseAgent[QuestionPlanningInput, QuestionPlanningOutput]):
    def __init__(self, llm):
        super().__init__(llm, QuestionPlanningOutput)

    def build_system_prompt(self) -> str:
        return PromptBuilder.inject_examples(
            SYSTEM_PROMPT,
            PromptBuilder.render_examples(EXAMPLES),
        )

    def build_user_prompt(
        self,
        input_data: QuestionPlanningInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
