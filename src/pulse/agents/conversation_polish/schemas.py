from typing import Optional

from pydantic import BaseModel, Field

from pulse.types import ScriptTurn, SpeakerProfile


class ConversationPolishInput(BaseModel):
    script_turn: ScriptTurn = Field(
        ...,
        description=(
            "The generated spoken turn whose dialogue should be polished "
            "without changing its speaker assignment or substantive meaning."
        ),
    )
    speaker: SpeakerProfile = Field(
        ...,
        description=(
            "The resolved profile of the speaker assigned to the script "
            "turn. The polished dialogue should remain consistent with this "
            "speaker's voice and delivery style."
        ),
    )
    previous_polished_script_turn: Optional[ScriptTurn] = Field(
        default=None,
        description=(
            "The immediately preceding polished spoken turn, when one "
            "exists, provided only for conversational and delivery "
            "continuity."
        ),
    )

    def to_llm_string(self) -> str:
        return (
            f"<script_turn>\n"
            f"{self.script_turn.spoken_text}\n"
            f"</script_turn>\n\n"
            f"<speaker_profile>\n"
            f"{self.speaker.to_llm_string()}\n"
            f"</speaker_profile>\n\n"
            f"<previous_polished_turn>\n"
            f"{self._render_previous_polished_turn()}\n"
            f"</previous_polished_turn>"
        )

    def _render_previous_polished_turn(self) -> str:
        if self.previous_polished_script_turn is None:
            return "No previous polished spoken turn exists."
        return self.previous_polished_script_turn.spoken_text


class ConversationPolishOutput(BaseModel):
    spoken_text: str = Field(
        ...,
        min_length=1,
        description=("The polished spoken dialogue for the provided script turn."),
    )
