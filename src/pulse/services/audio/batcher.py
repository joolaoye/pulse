from typing import Dict, List

from pulse.types import (
    DialogueBatch,
    DialogueBatchTurn,
    EpisodeScript,
    SpeakerVoiceBinding,
)

DEFAULT_MAX_DIALOGUE_BATCH_CHARACTERS = 1800


class DialogueBatcher:
    def __init__(
        self,
        *,
        max_characters_per_batch: int = DEFAULT_MAX_DIALOGUE_BATCH_CHARACTERS,
    ) -> None:
        if max_characters_per_batch <= 0:
            raise ValueError("Maximum dialogue batch character count must be positive.")

        self.max_characters_per_batch = max_characters_per_batch

    def batch(
        self,
        *,
        episode_script: EpisodeScript,
        speaker_voice_bindings: List[SpeakerVoiceBinding],
    ) -> List[DialogueBatch]:
        voice_id_by_speaker_id = self._build_voice_binding_lookup(
            speaker_voice_bindings=speaker_voice_bindings,
        )

        dialogue_batches: List[DialogueBatch] = []
        current_turns: List[DialogueBatchTurn] = []
        current_character_count = 0

        for script_turn_index, script_turn in enumerate(episode_script.turns):
            voice_id = voice_id_by_speaker_id.get(script_turn.speaker_id)

            if voice_id is None:
                raise ValueError(
                    "No synthesis voice binding was found for "
                    f"episode script speaker {script_turn.speaker_id!r}."
                )

            character_count = len(script_turn.spoken_text)

            if character_count > self.max_characters_per_batch:
                raise ValueError(
                    f"Episode script turn {script_turn_index} exceeds "
                    "the maximum dialogue batch character count. "
                    f"Maximum: {self.max_characters_per_batch}. "
                    f"Received: {character_count}."
                )

            if (
                current_turns
                and current_character_count + character_count > self.max_characters_per_batch
            ):
                dialogue_batches.append(
                    DialogueBatch(
                        batch_index=len(dialogue_batches),
                        turns=current_turns,
                    )
                )

                current_turns = []
                current_character_count = 0

            current_turns.append(
                DialogueBatchTurn(
                    script_turn_index=script_turn_index,
                    speaker_id=script_turn.speaker_id,
                    voice_id=voice_id,
                    spoken_text=script_turn.spoken_text,
                )
            )

            current_character_count += character_count

        if current_turns:
            dialogue_batches.append(
                DialogueBatch(
                    batch_index=len(dialogue_batches),
                    turns=current_turns,
                )
            )

        return dialogue_batches

    @staticmethod
    def _build_voice_binding_lookup(
        *,
        speaker_voice_bindings: List[SpeakerVoiceBinding],
    ) -> Dict[str, str]:
        if not speaker_voice_bindings:
            raise ValueError("Dialogue batching requires at least one speaker voice binding.")

        voice_id_by_speaker_id: Dict[str, str] = {}

        for binding in speaker_voice_bindings:
            if binding.speaker_id in voice_id_by_speaker_id:
                raise ValueError(
                    f"Multiple voice bindings were provided for speaker {binding.speaker_id!r}."
                )

            voice_id_by_speaker_id[binding.speaker_id] = binding.voice_id

        return voice_id_by_speaker_id
