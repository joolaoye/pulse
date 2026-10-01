from typing import List

from pydantic import BaseModel, Field, computed_field, model_validator


class DialogueBatchTurn(BaseModel):
    script_turn_index: int = Field(..., ge=0)
    speaker_id: str = Field(..., min_length=1)
    voice_id: str = Field(..., min_length=1)
    spoken_text: str = Field(..., min_length=1)


class DialogueBatch(BaseModel):
    batch_index: int = Field(..., ge=0)
    turns: List[DialogueBatchTurn] = Field(..., min_length=1)

    @computed_field
    @property
    def character_count(self) -> int:
        return sum(len(turn.spoken_text) for turn in self.turns)


class SynthesizedTurnTiming(BaseModel):
    script_turn_index: int = Field(..., ge=0)
    speaker_id: str = Field(..., min_length=1)
    start_time_seconds: float = Field(..., ge=0)
    end_time_seconds: float = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_time_range(self) -> "SynthesizedTurnTiming":
        if self.end_time_seconds < self.start_time_seconds:
            raise ValueError("A synthesized turn cannot end before it begins.")

        return self


class SynthesizedDialogueBatch(BaseModel):
    batch_index: int = Field(..., ge=0)
    audio_content: bytes = Field(..., min_length=1)
    output_format: str = Field(..., min_length=1)
    duration_seconds: float = Field(..., gt=0)
    turn_timings: List[SynthesizedTurnTiming] = Field(
        ...,
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_turn_timings(self) -> "SynthesizedDialogueBatch":
        script_turn_indexes = [timing.script_turn_index for timing in self.turn_timings]

        if script_turn_indexes != sorted(script_turn_indexes):
            raise ValueError("Synthesized turn timings must preserve script-turn order.")

        if len(script_turn_indexes) != len(set(script_turn_indexes)):
            raise ValueError(
                "A synthesized dialogue batch cannot contain duplicate script-turn timings."
            )

        latest_end_time = max(timing.end_time_seconds for timing in self.turn_timings)

        if self.duration_seconds < latest_end_time:
            raise ValueError(
                "Synthesized dialogue batch duration cannot be shorter "
                "than its latest turn end time."
            )

        return self


class EpisodeTurnTiming(BaseModel):
    script_turn_index: int = Field(..., ge=0)
    speaker_id: str = Field(..., min_length=1)
    start_time_seconds: float = Field(..., ge=0)
    end_time_seconds: float = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_time_range(self) -> "EpisodeTurnTiming":
        if self.end_time_seconds < self.start_time_seconds:
            raise ValueError("An assembled episode turn cannot end before it begins.")

        return self


class AssembledEpisodeAudio(BaseModel):
    output_format: str = Field(..., min_length=1)
    duration_seconds: float = Field(..., gt=0)
    turn_timings: List[EpisodeTurnTiming] = Field(
        ...,
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_turn_timings(self) -> "AssembledEpisodeAudio":
        script_turn_indexes = [timing.script_turn_index for timing in self.turn_timings]

        expected_script_turn_indexes = list(range(len(script_turn_indexes)))

        if script_turn_indexes != expected_script_turn_indexes:
            raise ValueError(
                "Episode turn timings must contain contiguous "
                "script-turn indexes in their original order."
            )

        latest_end_time = max(timing.end_time_seconds for timing in self.turn_timings)

        if self.duration_seconds < latest_end_time:
            raise ValueError(
                "Episode audio duration cannot be shorter than its latest turn end time."
            )

        return self


class StoredEpisodeAudio(BaseModel):
    object_key: str = Field(..., min_length=1)
    output_format: str = Field(..., min_length=1)
    content_type: str = Field(..., min_length=1)
    duration_seconds: float = Field(..., gt=0)
    size_bytes: int = Field(..., gt=0)
    turn_timings: List[EpisodeTurnTiming] = Field(
        ...,
        min_length=1,
    )
