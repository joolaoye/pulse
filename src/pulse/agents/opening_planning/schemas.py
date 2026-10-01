from pydantic import BaseModel, Field

from pulse.types import EpisodeBody


class OpeningPlanningInput(BaseModel):
    episode_body: EpisodeBody = Field(
        ...,
        description=(
            "The finalized ordered episode body that the opening must frame, "
            "preview, and naturally lead into. The opening should establish "
            "appropriate expectations for the planned segments without "
            "redefining their editorial scope."
        ),
    )
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        description=(
            "The exact duration budget available for the episode opening. "
            "The planned opening must be realistically accomplishable within "
            "this duration."
        ),
    )

    def to_llm_string(self) -> str:
        return (
            f"<target_duration_seconds>\n"
            f"{self.target_duration_seconds}\n"
            f"</target_duration_seconds>\n\n"
            f"<episode_body>\n"
            f"{self.episode_body.to_llm_string()}\n"
            f"</episode_body>"
        )


class OpeningPlanningOutput(BaseModel):
    objective: str = Field(
        ...,
        description=(
            "The episode-specific editorial objective of the opening. "
            "It describes what the listener should understand or feel "
            "before the main discussion begins."
        ),
    )
    hook_strategy: str = Field(
        ...,
        description=(
            "The editorial approach used to capture listener attention "
            "without scripting the hook itself."
        ),
    )
    podcast_introduction_goal: str = Field(
        ...,
        description=(
            "How the opening should briefly establish the podcast for the "
            "listener without scripting the exact introduction."
        ),
    )
    speaker_introduction_goal: str = Field(
        ...,
        description=(
            "How the opening should naturally establish the host and co-host "
            "before the main discussion begins without assigning exact turns "
            "or scripting their introductions."
        ),
    )
    listener_promise: str = Field(
        ...,
        description=(
            "The value proposition the opening should communicate, describing "
            "what the listener should expect to understand or gain by "
            "continuing with the episode."
        ),
    )
    transition_goal: str = Field(
        ...,
        description=(
            "How the opening should naturally hand the conversation into "
            "the first episode beat without scripting the transition itself."
        ),
    )
