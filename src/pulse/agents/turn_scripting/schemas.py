from typing import List, Optional

from pydantic import BaseModel, Field

from pulse.types import (
    PodcastProfile,
    ProcessedSignal,
    ScriptTurn,
    SpeakerProfile,
    Turn,
)


class TurnScriptingInput(BaseModel):
    turn: Turn = Field(
        ...,
        description=(
            "The finalized planned conversational turn that defines what "
            "this contribution must accomplish and its authoritative "
            "duration budget."
        ),
    )
    speaker: SpeakerProfile = Field(
        ...,
        description=("The resolved profile of the speaker assigned to this turn."),
    )
    podcast_profile: PodcastProfile = Field(
        ...,
        description=(
            "The podcast-level profile that defines the show's purpose, "
            "audience, editorial style, and conversational style."
        ),
    )
    planning_context: str = Field(
        ...,
        min_length=1,
        description=("The finalized local editorial context surrounding this turn."),
    )
    source_context: List[ProcessedSignal] = Field(
        default_factory=list,
        description=("The approved source material available for grounding this turn."),
    )
    previous_script_turn: Optional[ScriptTurn] = Field(
        default=None,
        description=(
            "The immediately preceding scripted turn, provided only for conversational continuity."
        ),
    )

    def to_llm_string(self) -> str:
        return (
            f"<planned_turn>\n"
            f"{self.turn.to_llm_string()}\n"
            f"</planned_turn>\n\n"
            f"<speaker_profile>\n"
            f"{self.speaker.to_llm_string()}\n"
            f"</speaker_profile>\n\n"
            f"<podcast_profile>\n"
            f"{self.podcast_profile.to_llm_string()}\n"
            f"</podcast_profile>\n\n"
            f"<planning_context>\n"
            f"{self.planning_context}\n"
            f"</planning_context>\n\n"
            f"<source_context>\n"
            f"{self._render_source_context()}\n"
            f"</source_context>\n\n"
            f"<previous_spoken_turn>\n"
            f"{self._render_previous_spoken_turn()}\n"
            f"</previous_spoken_turn>"
        )

    def _render_source_context(self) -> str:
        if not self.source_context:
            return "No direct source material is provided for this turn."

        return "\n\n---\n\n".join(self._render_signal(signal) for signal in self.source_context)

    @staticmethod
    def _render_signal(signal: ProcessedSignal) -> str:
        return (
            f"Title:\n"
            f"{signal.title}\n\n"
            f"Source:\n"
            f"{signal.source}\n\n"
            f"Relevance Score:\n"
            f"{signal.relevance_score}\n\n"
            f"Context:\n"
            f"{signal.markdown_context}"
        )

    def _render_previous_spoken_turn(self) -> str:
        if self.previous_script_turn is None:
            return "No previous spoken turn exists."
        return self.previous_script_turn.spoken_text


class TurnScriptingOutput(BaseModel):
    spoken_text: str = Field(
        ...,
        min_length=1,
        description=("The exact spoken dialogue generated for the corresponding planned turn."),
    )
