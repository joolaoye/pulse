from pulse.agents._base import BaseAgent
from pulse.agents.conversation_angle_planning.examples import EXAMPLES
from pulse.agents.conversation_angle_planning.schemas import (
    ConversationAnglePlanningInput,
    ConversationAnglePlanningOutput,
)
from pulse.agents.conversation_angle_planning.system_prompt import SYSTEM_PROMPT
from pulse.agents.conversation_angle_planning.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL
from pulse.infrastructure.prompting import PromptBuilder

CONVERSATION_ANGLE_MODEL = SONNET_MODEL
CONVERSATION_ANGLE_TEMPERATURE = 0.5
CONVERSATION_ANGLE_MAX_TOKENS = 768


class ConversationAnglePlanningAgent(
    BaseAgent[ConversationAnglePlanningInput, ConversationAnglePlanningOutput]
):
    def __init__(self, llm):
        super().__init__(llm, ConversationAnglePlanningOutput)

    def build_system_prompt(self) -> str:
        return PromptBuilder.inject_examples(
            SYSTEM_PROMPT,
            PromptBuilder.render_examples(EXAMPLES),
        )

    def build_user_prompt(
        self,
        input_data: ConversationAnglePlanningInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
