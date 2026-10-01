from pulse.infrastructure.tts.elevenlabs.models import (
    ElevenLabsDialogueInput,
    ElevenLabsDialogueResult,
    ElevenLabsVoiceSegment,
)
from pulse.services.audio.synthesizer import DialogueSynthesizer
from pulse.types import DialogueBatch, DialogueBatchTurn


class _Provider:
    def __init__(self, result: ElevenLabsDialogueResult) -> None:
        self.result = result
        self.dialogue_inputs: list[list[ElevenLabsDialogueInput]] = []

    @property
    def output_format(self) -> str:
        return "mp3_44100_128"

    async def synthesize(
        self,
        *,
        dialogue_inputs: list[ElevenLabsDialogueInput],
    ) -> ElevenLabsDialogueResult:
        self.dialogue_inputs.append(dialogue_inputs)
        return self.result


def _segment(
    *,
    start_time_seconds: float,
    end_time_seconds: float,
    character_start_index: int,
    character_end_index: int,
) -> ElevenLabsVoiceSegment:
    return ElevenLabsVoiceSegment(
        voice_id="voice-host",
        start_time_seconds=start_time_seconds,
        end_time_seconds=end_time_seconds,
        character_start_index=character_start_index,
        character_end_index=character_end_index,
        dialogue_input_index=0,
    )


async def test_multiple_segments_collapse_to_one_turn_window() -> None:
    provider = _Provider(
        ElevenLabsDialogueResult(
            audio_content=b"audio",
            voice_segments=[
                _segment(
                    start_time_seconds=0.5,
                    end_time_seconds=1.1,
                    character_start_index=5,
                    character_end_index=11,
                ),
                _segment(
                    start_time_seconds=0.0,
                    end_time_seconds=0.4,
                    character_start_index=0,
                    character_end_index=5,
                ),
            ],
        )
    )
    batch = DialogueBatch(
        batch_index=0,
        turns=[
            DialogueBatchTurn(
                script_turn_index=3,
                speaker_id="host",
                voice_id="voice-host",
                spoken_text="Hello there",
            )
        ],
    )

    synthesized = await DialogueSynthesizer(dialogue_provider=provider).synthesize_batch(
        dialogue_batch=batch,
    )

    assert provider.dialogue_inputs == [
        [ElevenLabsDialogueInput(text="Hello there", voice_id="voice-host")]
    ]
    assert synthesized.duration_seconds == 1.1
    assert synthesized.output_format == "mp3_44100_128"
    assert [
        (
            timing.script_turn_index,
            timing.speaker_id,
            timing.start_time_seconds,
            timing.end_time_seconds,
        )
        for timing in synthesized.turn_timings
    ] == [(3, "host", 0.0, 1.1)]
