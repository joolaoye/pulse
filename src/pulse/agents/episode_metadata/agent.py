from pulse.agents._base import BaseAgent
from pulse.agents.episode_metadata.schemas import (
    EpisodeMetadataGenerationInput,
    EpisodeMetadataGenerationOutput,
)
from pulse.agents.episode_metadata.system_prompt import SYSTEM_PROMPT
from pulse.agents.episode_metadata.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import HAIKU_MODEL

EPISODE_METADATA_GENERATION_MODEL = HAIKU_MODEL
EPISODE_METADATA_GENERATION_TEMPERATURE = 0.3
EPISODE_METADATA_GENERATION_MAX_TOKENS = 768


class EpisodeMetadataGenerationAgent(
    BaseAgent[EpisodeMetadataGenerationInput, EpisodeMetadataGenerationOutput]
):
    def __init__(self, llm):
        super().__init__(llm, EpisodeMetadataGenerationOutput)

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_user_prompt(
        self,
        input_data: EpisodeMetadataGenerationInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
