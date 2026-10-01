from typing import List

from pydantic import BaseModel, Field

from pulse.agents._shared import TurnPlanningOutputItem
from pulse.types import Beat, SpeakerProfile


class BodyTurnPlanningInput(BaseModel):
    beat: Beat = Field(
        ...,
        description=(
            "The finalized conversational beat whose speaker-aware turn "
            "sequence must be planned. The beat defines the authoritative "
            "purpose, conversation angle, questions, segue guidance, source "
            "selection, and exact duration budget that the planned turns "
            "must realize."
        ),
    )
    speakers: List[SpeakerProfile] = Field(
        ...,
        min_length=1,
        description=(
            "The authoritative speaker profiles available for assignment "
            "across the conversational turns planned for this beat."
        ),
    )

    def to_llm_string(self) -> str:
        speakers = "\n\n---\n\n".join(speaker.to_llm_string() for speaker in self.speakers)
        return (
            f"<beat>\n"
            f"{self.beat.to_llm_string()}\n"
            f"</beat>\n\n"
            f"<available_speakers>\n"
            f"{speakers}\n"
            f"</available_speakers>"
        )


class BodyTurnPlanningOutput(BaseModel):
    turns: List[TurnPlanningOutputItem] = Field(
        ...,
        min_length=1,
        description=(
            "The ordered speaker-aware conversational turns planned for the "
            "current beat. Together, the turns must realize the beat's "
            "purpose, conversation angle, questions, and segue guidance "
            "within its authoritative duration budget. Each turn defines "
            "its relative duration weight for deterministic allocation by "
            "the body turn planner."
        ),
    )
