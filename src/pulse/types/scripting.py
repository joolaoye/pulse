from typing import List

from pydantic import BaseModel, Field


class ScriptTurn(BaseModel):
    speaker_id: str = Field(
        ...,
        min_length=1,
        description=(
            "The exact identifier of the speaker assigned to the corresponding planned turn."
        ),
    )
    spoken_text: str = Field(
        ...,
        min_length=1,
        description=(
            "The exact speech-ready dialogue generated for the corresponding planned turn."
        ),
    )

    def to_llm_string(
        self,
        *,
        turn_number: int,
    ) -> str:
        return f"## Turn {turn_number}\n\n**Spoken text:**\n\n{self.spoken_text}"


class EpisodeScript(BaseModel):
    turns: List[ScriptTurn] = Field(
        ...,
        min_length=1,
        description=(
            "The complete ordered sequence of spoken turns that make up the "
            "episode, from the opening through the body and closing."
        ),
    )

    def to_llm_string(self) -> str:
        return "\n\n".join(
            script_turn.to_llm_string(turn_number=turn_number)
            for turn_number, script_turn in enumerate(
                self.turns,
                start=1,
            )
        )
