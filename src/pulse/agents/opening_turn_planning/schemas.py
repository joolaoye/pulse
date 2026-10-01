from typing import List

from pydantic import BaseModel, Field

from pulse.agents._shared import TurnPlanningOutputItem
from pulse.types import EpisodeOpening, Segment, SpeakerProfile


class OpeningTurnPlanningInput(BaseModel):
    episode_opening: EpisodeOpening = Field(
        ...,
        description=(
            "The finalized editorial plan for the episode opening that the "
            "planned turns must realize."
        ),
    )
    first_segment: Segment = Field(
        ...,
        description=(
            "The first major segment of the finalized episode body. It "
            "defines the substantive discussion that follows the opening, "
            "including the first conversational beat that the opening must "
            "naturally lead into."
        ),
    )
    speakers: List[SpeakerProfile] = Field(
        ...,
        min_length=1,
        description=(
            "The authoritative speaker profiles available for assignment "
            "across the planned opening turns."
        ),
    )

    def to_llm_string(self) -> str:
        speakers = "\n\n---\n\n".join(speaker.to_llm_string() for speaker in self.speakers)
        return (
            f"<episode_opening>\n"
            f"{self.episode_opening.to_llm_string()}\n"
            f"</episode_opening>\n\n"
            f"<first_segment>\n"
            f"{self.first_segment.to_llm_string()}\n"
            f"</first_segment>\n\n"
            f"<available_speakers>\n"
            f"{speakers}\n"
            f"</available_speakers>"
        )


class OpeningTurnPlanningOutput(BaseModel):
    turns: List[TurnPlanningOutputItem] = Field(
        ...,
        min_length=1,
        description=(
            "The ordered speaker-aware conversational turns planned for the "
            "episode opening. Collectively, the turns must execute the opening "
            "strategy, communicate the listener promise, and transition "
            "naturally into the first segment without prematurely conducting "
            "its substantive discussion."
        ),
    )
