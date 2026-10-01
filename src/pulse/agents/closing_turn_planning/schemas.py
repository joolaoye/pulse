from typing import List

from pydantic import BaseModel, Field

from pulse.agents._shared import TurnPlanningOutputItem
from pulse.types import EpisodeClosing, Segment, SpeakerProfile


class ClosingTurnPlanningInput(BaseModel):
    episode_closing: EpisodeClosing = Field(
        ...,
        description=(
            "The finalized editorial plan for the episode closing that the "
            "planned turns must realize."
        ),
    )
    final_segment: Segment = Field(
        ...,
        description=(
            "The final major segment of the finalized episode body. It "
            "provides the immediate conversational context from which the "
            "closing must naturally emerge, including the final substantive "
            "beat that precedes the closing."
        ),
    )
    speakers: List[SpeakerProfile] = Field(
        ...,
        min_length=1,
        description=(
            "The authoritative speaker profiles available for assignment "
            "across the planned closing turns."
        ),
    )

    def to_llm_string(self) -> str:
        speakers = "\n\n---\n\n".join(speaker.to_llm_string() for speaker in self.speakers)
        return (
            f"<episode_closing>\n"
            f"{self.episode_closing.to_llm_string()}\n"
            f"</episode_closing>\n\n"
            f"<final_segment>\n"
            f"{self.final_segment.to_llm_string()}\n"
            f"</final_segment>\n\n"
            f"<available_speakers>\n"
            f"{speakers}\n"
            f"</available_speakers>"
        )


class ClosingTurnPlanningOutput(BaseModel):
    turns: List[TurnPlanningOutputItem] = Field(
        ...,
        min_length=1,
        description=(
            "The ordered speaker-aware conversational turns planned for the "
            "episode closing. Together, the turns must realize the finalized "
            "closing strategy, communicate its final supported takeaway, and "
            "bring the conversation to a natural conclusion. Each turn also "
            "defines its relative duration weight for deterministic allocation "
            "within the closing's authoritative duration budget."
        ),
    )
