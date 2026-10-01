from pydantic import BaseModel, Field, field_validator

from pulse.types import EpisodeScript


class EpisodeMetadataGenerationInput(BaseModel):
    episode_script: EpisodeScript = Field(
        ...,
        description=(
            "The final ordered episode script from which the listener-facing "
            "title and description must be generated."
        ),
    )

    def to_llm_string(self) -> str:
        return (
            f"<finalized_episode_script>\n"
            f"{self.episode_script.to_llm_string()}\n"
            f"</finalized_episode_script>"
        )


class EpisodeMetadataGenerationOutput(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        description=(
            "A concise and specific podcast episode title grounded in the final episode script."
        ),
    )
    description: str = Field(
        ...,
        min_length=1,
        description=(
            "A listener-facing episode description that accurately summarizes "
            "the final episode script."
        ),
    )

    @field_validator("title", "description")
    @classmethod
    def validate_nonblank_text(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Generated episode metadata must not contain blank text.")
        return normalized_value
