from pulse.agents._base import BaseAgent
from pulse.agents.conversation_polish.schemas import (
    ConversationPolishInput,
    ConversationPolishOutput,
)
from pulse.agents.conversation_polish.system_prompt import SYSTEM_PROMPT
from pulse.agents.conversation_polish.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL

CONVERSATION_POLISH_MODEL = SONNET_MODEL
CONVERSATION_POLISH_TEMPERATURE = 0.4
CONVERSATION_POLISH_MAX_TOKENS = 4096

NO_RUNTIME_DELIVERY_INSTRUCTIONS = """
No provider-specific delivery instructions were supplied.

Do not add delivery tags, performance cues, stage directions, SSML, XML, or
other synthesis-specific annotations.

Return clean spoken dialogue shaped only through wording and punctuation.
""".strip()

NO_RUNTIME_DELIVERY_EXAMPLES = """
No provider-specific delivery examples were supplied.
""".strip()


class ConversationPolishAgent(BaseAgent[ConversationPolishInput, ConversationPolishOutput]):
    def __init__(
        self,
        llm,
        runtime_delivery_instructions: str = "",
        runtime_delivery_examples: str = "",
    ) -> None:
        super().__init__(llm, ConversationPolishOutput)

        self._runtime_delivery_instructions = (
            runtime_delivery_instructions.strip() or NO_RUNTIME_DELIVERY_INSTRUCTIONS
        )
        self._runtime_delivery_examples = (
            runtime_delivery_examples.strip() or NO_RUNTIME_DELIVERY_EXAMPLES
        )

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(
            runtime_delivery_instructions=self._runtime_delivery_instructions,
            runtime_delivery_examples=self._runtime_delivery_examples,
        )

    def build_user_prompt(
        self,
        input_data: ConversationPolishInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
