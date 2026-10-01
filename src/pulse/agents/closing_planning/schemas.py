from pydantic import BaseModel, Field

from pulse.types import EpisodeBody


class ClosingPlanningInput(BaseModel):
    episode_body: EpisodeBody = Field(
        ...,
        description=(
            "The finalized ordered episode body that the closing must resolve, "
            "synthesize, and naturally bring to a conclusion. The closing "
            "should reflect the discussion actually developed across the "
            "planned segments and beats without redefining their editorial "
            "scope."
        ),
    )
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        description=(
            "The exact duration budget available for the episode closing. "
            "The planned closing must be realistically accomplishable within "
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


class ClosingPlanningOutput(BaseModel):
    objective: str = Field(
        ...,
        description=(
            "The episode-specific editorial objective of the closing. "
            "It describes what the ending should accomplish after the "
            "final episode beat has concluded."
        ),
    )
    resolution_strategy: str = Field(
        ...,
        description=(
            "The editorial approach used to bring the episode to a "
            "satisfying conclusion without scripting the ending itself."
        ),
    )
    final_takeaway: str = Field(
        ...,
        description=(
            "The final supported observation, insight, or point of reflection "
            "that should remain with the listener as the episode ends. It does "
            "not need to summarize or unify the entire episode."
        ),
    )
    closing_goal: str = Field(
        ...,
        description=(
            "The desired final conversational experience and how the "
            "episode should come to rest after its substantive discussion "
            "has concluded, without scripting narration or dialogue."
        ),
    )
