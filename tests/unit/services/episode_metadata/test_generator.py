from pydantic import ValidationError
import pytest

from pulse.agents.episode_metadata.schemas import EpisodeMetadataGenerationOutput
from pulse.services.episode_metadata.generator import EpisodeMetadataGenerator
from pulse.types import EpisodeMetadata, EpisodeScript, ScriptTurn


def _script() -> EpisodeScript:
    return EpisodeScript(turns=[ScriptTurn(speaker_id="host", spoken_text="The episode")])


class _MetadataAgent:
    def __init__(self, output: EpisodeMetadataGenerationOutput) -> None:
        self.output = output
        self.inputs = []

    async def arun(self, *, input_data):
        self.inputs.append(input_data)
        return self.output


async def test_metadata_maps_title_and_description_from_the_script() -> None:
    script = _script()
    agent = _MetadataAgent(
        EpisodeMetadataGenerationOutput(
            title="A specific title",
            description="A listener-facing description",
        )
    )

    metadata = await EpisodeMetadataGenerator(
        episode_metadata_generation_agent=agent,
    ).generate(episode_script=script)

    assert agent.inputs[0].episode_script is script
    assert metadata == EpisodeMetadata(
        title="A specific title",
        description="A listener-facing description",
    )


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("   ", "Description"),
        ("Title", "   "),
    ],
)
def test_blank_episode_metadata_is_rejected(title: str, description: str) -> None:
    with pytest.raises(ValidationError):
        EpisodeMetadata(title=title, description=description)
