from pulse.agents._base import BaseAgent
from pulse.agents.turn_scripting.schemas import (
    TurnScriptingInput,
    TurnScriptingOutput,
)
from pulse.agents.turn_scripting.system_prompt import SYSTEM_PROMPT
from pulse.agents.turn_scripting.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL

TURN_SCRIPTING_MODEL = SONNET_MODEL
TURN_SCRIPTING_TEMPERATURE = 0.6
TURN_SCRIPTING_MAX_TOKENS = 1024


class TurnScriptingAgent(BaseAgent[TurnScriptingInput, TurnScriptingOutput]):
    def __init__(self, llm) -> None:
        super().__init__(llm, TurnScriptingOutput)

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_user_prompt(
        self,
        input_data: TurnScriptingInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
