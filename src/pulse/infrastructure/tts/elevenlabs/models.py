from typing import List, Optional

from pydantic import (
    BaseModel,
    Field,
)


class ElevenLabsVoiceSegment(BaseModel):
    voice_id: str = Field(
        ...,
        min_length=1,
        description=("The ElevenLabs voice identifier used for the audio segment."),
    )

    start_time_seconds: float = Field(
        ...,
        ge=0,
        description=("The batch-relative start time of the voice segment."),
    )

    end_time_seconds: float = Field(
        ...,
        ge=0,
        description=("The batch-relative end time of the voice segment."),
    )

    character_start_index: int = Field(
        ...,
        ge=0,
        description=("The inclusive character index at which the voice segment begins."),
    )

    character_end_index: int = Field(
        ...,
        ge=0,
        description=("The exclusive character index at which the voice segment ends."),
    )

    dialogue_input_index: int = Field(
        ...,
        ge=0,
        description=("The index of the dialogue input associated with the voice segment."),
    )


class ElevenLabsDialogueInput(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        description=("The exact spoken text that ElevenLabs should synthesize."),
    )

    voice_id: str = Field(
        ...,
        min_length=1,
        description=("The ElevenLabs voice identifier used to synthesize the dialogue input."),
    )


class ElevenLabsDialogueResult(BaseModel):
    audio_content: bytes = Field(
        ...,
        min_length=1,
        description=("The decoded audio bytes returned by ElevenLabs."),
    )

    voice_segments: List[ElevenLabsVoiceSegment] = Field(
        ...,
        min_length=1,
        description=("The batch-relative voice segments returned for the synthesized dialogue."),
    )


class ElevenLabsProviderError(RuntimeError):
    def __init__(
        self,
        *,
        message: str,
        retryable: bool,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(message)

        self.message = message

        self.retryable = retryable

        self.status_code = status_code

        self.error_code = error_code
