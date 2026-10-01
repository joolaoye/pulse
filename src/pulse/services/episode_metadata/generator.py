from pulse.agents import (
    EpisodeMetadataGenerationAgent,
    EpisodeMetadataGenerationInput,
)
from pulse.types import EpisodeMetadata, EpisodeScript


class EpisodeMetadataGenerator:
    def __init__(
        self,
        *,
        episode_metadata_generation_agent: EpisodeMetadataGenerationAgent,
    ) -> None:
        self.episode_metadata_generation_agent = episode_metadata_generation_agent

    async def generate(
        self,
        *,
        episode_script: EpisodeScript,
    ) -> EpisodeMetadata:
        output = await self.episode_metadata_generation_agent.arun(
            input_data=EpisodeMetadataGenerationInput(
                episode_script=episode_script,
            )
        )

        return EpisodeMetadata(
            title=output.title,
            description=output.description,
        )
