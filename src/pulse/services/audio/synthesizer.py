from typing import Dict, List

from pulse.infrastructure.tts import (
    ElevenLabsDialogueInput,
    ElevenLabsDialogueProvider,
    ElevenLabsDialogueResult,
    ElevenLabsVoiceSegment,
)
from pulse.types import (
    DialogueBatch,
    DialogueBatchTurn,
    SynthesizedDialogueBatch,
    SynthesizedTurnTiming,
)


class DialogueSynthesizer:
    def __init__(
        self,
        *,
        dialogue_provider: ElevenLabsDialogueProvider,
    ) -> None:
        self.dialogue_provider = dialogue_provider

    async def synthesize(
        self,
        *,
        dialogue_batches: List[DialogueBatch],
    ) -> List[SynthesizedDialogueBatch]:
        self._validate_dialogue_batches(
            dialogue_batches=dialogue_batches,
        )

        synthesized_batches: List[SynthesizedDialogueBatch] = []

        for dialogue_batch in dialogue_batches:
            synthesized_batch = await self._synthesize_dialogue_batch(
                dialogue_batch=dialogue_batch,
            )

            self._validate_synthesized_dialogue_batch(
                dialogue_batch=dialogue_batch,
                synthesized_dialogue_batch=synthesized_batch,
            )

            synthesized_batches.append(synthesized_batch)

        return synthesized_batches

    async def synthesize_batch(
        self,
        *,
        dialogue_batch: DialogueBatch,
    ) -> SynthesizedDialogueBatch:
        self._validate_dialogue_batch(
            dialogue_batch=dialogue_batch,
        )

        synthesized_batch = await self._synthesize_dialogue_batch(
            dialogue_batch=dialogue_batch,
        )

        self._validate_synthesized_dialogue_batch(
            dialogue_batch=dialogue_batch,
            synthesized_dialogue_batch=synthesized_batch,
        )

        return synthesized_batch

    async def _synthesize_dialogue_batch(
        self,
        *,
        dialogue_batch: DialogueBatch,
    ) -> SynthesizedDialogueBatch:
        dialogue_result = await self.dialogue_provider.synthesize(
            dialogue_inputs=self._create_dialogue_inputs(
                dialogue_batch=dialogue_batch,
            )
        )

        turn_timings = self._create_turn_timings(
            dialogue_batch=dialogue_batch,
            dialogue_result=dialogue_result,
        )

        return SynthesizedDialogueBatch(
            batch_index=dialogue_batch.batch_index,
            audio_content=dialogue_result.audio_content,
            output_format=self.dialogue_provider.output_format,
            duration_seconds=max(timing.end_time_seconds for timing in turn_timings),
            turn_timings=turn_timings,
        )

    @staticmethod
    def _create_dialogue_inputs(
        *,
        dialogue_batch: DialogueBatch,
    ) -> List[ElevenLabsDialogueInput]:
        return [
            ElevenLabsDialogueInput(
                text=turn.spoken_text,
                voice_id=turn.voice_id,
            )
            for turn in dialogue_batch.turns
        ]

    @staticmethod
    def _create_turn_timings(
        *,
        dialogue_batch: DialogueBatch,
        dialogue_result: ElevenLabsDialogueResult,
    ) -> List[SynthesizedTurnTiming]:
        segments_by_input: Dict[
            int,
            List[ElevenLabsVoiceSegment],
        ] = {}

        for segment in dialogue_result.voice_segments:
            segments_by_input.setdefault(
                segment.dialogue_input_index,
                [],
            ).append(segment)

        return [
            SynthesizedTurnTiming(
                script_turn_index=turn.script_turn_index,
                speaker_id=turn.speaker_id,
                start_time_seconds=min(
                    segment.start_time_seconds for segment in segments_by_input[input_index]
                ),
                end_time_seconds=max(
                    segment.end_time_seconds for segment in segments_by_input[input_index]
                ),
            )
            for input_index, turn in enumerate(dialogue_batch.turns)
        ]

    def _validate_dialogue_batches(
        self,
        *,
        dialogue_batches: List[DialogueBatch],
    ) -> None:
        if not dialogue_batches:
            raise ValueError("Dialogue synthesis requires at least one dialogue batch.")

        observed_script_turn_indexes: List[int] = []

        for expected_batch_index, dialogue_batch in enumerate(dialogue_batches):
            self._validate_dialogue_batch(
                dialogue_batch=dialogue_batch,
            )

            if dialogue_batch.batch_index != expected_batch_index:
                raise ValueError(
                    "Dialogue synthesis received a non-contiguous "
                    f"batch index. Expected {expected_batch_index}, "
                    f"received {dialogue_batch.batch_index}."
                )

            observed_script_turn_indexes.extend(
                turn.script_turn_index for turn in dialogue_batch.turns
            )

        expected_script_turn_indexes = list(range(len(observed_script_turn_indexes)))

        if observed_script_turn_indexes != expected_script_turn_indexes:
            raise ValueError(
                "Dialogue synthesis received dialogue batches with "
                "changed or non-contiguous script-turn indexes."
            )

    def _validate_dialogue_batch(
        self,
        *,
        dialogue_batch: DialogueBatch,
    ) -> None:
        if dialogue_batch.batch_index < 0:
            raise ValueError(
                "Dialogue synthesis received a negative dialogue "
                f"batch index. Received {dialogue_batch.batch_index}."
            )

        if not dialogue_batch.turns:
            raise ValueError(
                "Dialogue synthesis received an empty dialogue batch "
                f"at index {dialogue_batch.batch_index}."
            )

        observed_script_turn_indexes: List[int] = []

        for dialogue_batch_turn in dialogue_batch.turns:
            self._validate_dialogue_batch_turn(
                dialogue_batch=dialogue_batch,
                dialogue_batch_turn=dialogue_batch_turn,
            )

            observed_script_turn_indexes.append(dialogue_batch_turn.script_turn_index)

        first_script_turn_index = observed_script_turn_indexes[0]

        expected_script_turn_indexes = list(
            range(
                first_script_turn_index,
                first_script_turn_index + len(observed_script_turn_indexes),
            )
        )

        if observed_script_turn_indexes != expected_script_turn_indexes:
            raise ValueError(
                "Dialogue synthesis received a dialogue batch with "
                "changed or non-contiguous script-turn indexes. "
                f"Batch index: {dialogue_batch.batch_index}."
            )

    @staticmethod
    def _validate_dialogue_batch_turn(
        *,
        dialogue_batch: DialogueBatch,
        dialogue_batch_turn: DialogueBatchTurn,
    ) -> None:
        if dialogue_batch_turn.script_turn_index < 0:
            raise ValueError(
                "Dialogue synthesis received a negative script-turn "
                f"index. Batch index: {dialogue_batch.batch_index}. "
                f"Script-turn index: "
                f"{dialogue_batch_turn.script_turn_index}."
            )

        if not dialogue_batch_turn.speaker_id.strip():
            raise ValueError(
                "Dialogue synthesis received a blank speaker "
                f"identifier. Batch index: "
                f"{dialogue_batch.batch_index}. Script-turn index: "
                f"{dialogue_batch_turn.script_turn_index}."
            )

        if not dialogue_batch_turn.voice_id.strip():
            raise ValueError(
                "Dialogue synthesis received a blank voice "
                f"identifier. Batch index: "
                f"{dialogue_batch.batch_index}. Script-turn index: "
                f"{dialogue_batch_turn.script_turn_index}."
            )

        if not dialogue_batch_turn.spoken_text.strip():
            raise ValueError(
                "Dialogue synthesis received blank spoken text. "
                f"Batch index: {dialogue_batch.batch_index}. "
                f"Script-turn index: "
                f"{dialogue_batch_turn.script_turn_index}."
            )

    def _validate_synthesized_dialogue_batch(
        self,
        *,
        dialogue_batch: DialogueBatch,
        synthesized_dialogue_batch: SynthesizedDialogueBatch,
    ) -> None:
        if synthesized_dialogue_batch.batch_index != dialogue_batch.batch_index:
            raise ValueError(
                "Dialogue synthesis changed a dialogue batch index. "
                f"Expected {dialogue_batch.batch_index}, received "
                f"{synthesized_dialogue_batch.batch_index}."
            )

        if not synthesized_dialogue_batch.audio_content:
            raise ValueError(
                "Dialogue synthesis returned empty audio content "
                f"for batch {dialogue_batch.batch_index}."
            )

        if not synthesized_dialogue_batch.output_format.strip():
            raise ValueError(
                "Dialogue synthesis returned a blank output format "
                f"for batch {dialogue_batch.batch_index}."
            )

        if synthesized_dialogue_batch.duration_seconds <= 0:
            raise ValueError(
                "Dialogue synthesis returned a non-positive duration "
                f"for batch {dialogue_batch.batch_index}."
            )

        if len(synthesized_dialogue_batch.turn_timings) != len(dialogue_batch.turns):
            raise ValueError(
                "Dialogue synthesis changed the turn count for batch "
                f"{dialogue_batch.batch_index}. Expected "
                f"{len(dialogue_batch.turns)}, received "
                f"{len(synthesized_dialogue_batch.turn_timings)}."
            )

        for dialogue_turn, synthesized_timing in zip(
            dialogue_batch.turns,
            synthesized_dialogue_batch.turn_timings,
            strict=True,
        ):
            self._validate_synthesized_turn_timing(
                dialogue_batch=dialogue_batch,
                dialogue_batch_turn=dialogue_turn,
                synthesized_turn_timing=synthesized_timing,
            )

    @staticmethod
    def _validate_synthesized_turn_timing(
        *,
        dialogue_batch: DialogueBatch,
        dialogue_batch_turn: DialogueBatchTurn,
        synthesized_turn_timing: SynthesizedTurnTiming,
    ) -> None:
        if synthesized_turn_timing.script_turn_index != dialogue_batch_turn.script_turn_index:
            raise ValueError(
                "Dialogue synthesis changed a script-turn index. "
                f"Batch index: {dialogue_batch.batch_index}. "
                f"Expected {dialogue_batch_turn.script_turn_index}, "
                f"received "
                f"{synthesized_turn_timing.script_turn_index}."
            )

        if synthesized_turn_timing.speaker_id != dialogue_batch_turn.speaker_id:
            raise ValueError(
                "Dialogue synthesis changed a script-turn speaker. "
                f"Batch index: {dialogue_batch.batch_index}. "
                f"Script-turn index: "
                f"{dialogue_batch_turn.script_turn_index}. "
                f"Expected '{dialogue_batch_turn.speaker_id}', "
                f"received '{synthesized_turn_timing.speaker_id}'."
            )
