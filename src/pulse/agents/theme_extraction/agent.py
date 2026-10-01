from pulse.agents._base import BaseAgent
from pulse.agents.theme_extraction.examples import EXAMPLES
from pulse.agents.theme_extraction.schemas import ThemeExtractionInput
from pulse.agents.theme_extraction.system_prompt import SYSTEM_PROMPT
from pulse.agents.theme_extraction.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import HAIKU_MODEL
from pulse.infrastructure.prompting import PromptBuilder
from pulse.types import Theme

THEME_EXTRACTION_MODEL = HAIKU_MODEL
THEME_EXTRACTION_TEMPERATURE = 0.2
THEME_EXTRACTION_MAX_TOKENS = 512


class ThemeExtractionAgent(BaseAgent[ThemeExtractionInput, Theme]):
    def __init__(self, llm):
        super().__init__(llm, Theme)

    def build_system_prompt(self) -> str:
        return PromptBuilder.inject_examples(
            SYSTEM_PROMPT,
            PromptBuilder.render_examples(EXAMPLES),
        )

    def build_user_prompt(
        self,
        input_data: ThemeExtractionInput,
    ) -> str:
        return USER_PROMPT.format(
            signals_markdown=input_data.to_llm_string(),
        )
