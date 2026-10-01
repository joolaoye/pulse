from contextlib import suppress
from typing import List

from pulse.infrastructure.storage import AudioRepository
from pulse.services.audio.assembler import AudioAssembler
from pulse.services.audio.batcher import DialogueBatcher
from pulse.services.audio.synthesizer import DialogueSynthesizer
from pulse.types import (
    EpisodeScript,
    SpeakerVoiceBinding,
    StoredEpisodeAudio,
)


class AudioProducer:
    def __init__(
        self,
        *,
        dialogue_batcher: DialogueBatcher,
        dialogue_synthesizer: DialogueSynthesizer,
        audio_assembler: AudioAssembler,
        audio_repository: AudioRepository,
    ) -> None:
        self.dialogue_batcher = dialogue_batcher
        self.dialogue_synthesizer = dialogue_synthesizer
        self.audio_assembler = audio_assembler
        self.audio_repository = audio_repository

    async def produce(
        self,
        *,
        show_id: str,
        episode_id: str,
        episode_script: EpisodeScript,
        speaker_voice_bindings: List[SpeakerVoiceBinding],
    ) -> StoredEpisodeAudio:
        dialogue_batches = self.dialogue_batcher.batch(
            episode_script=episode_script,
            speaker_voice_bindings=speaker_voice_bindings,
        )
        assembly = self.audio_assembler.create_session()
        upload = await self.audio_repository.begin_upload(
            show_id=show_id,
            episode_id=episode_id,
            output_format=self.audio_assembler.output_format,
        )

        try:
            for dialogue_batch in dialogue_batches:
                synthesized_batch = await self.dialogue_synthesizer.synthesize_batch(
                    dialogue_batch=dialogue_batch,
                )
                chunk = assembly.process_batch(
                    synthesized_dialogue_batch=synthesized_batch,
                )
                await upload.write(
                    content=chunk.audio_content,
                )
                del synthesized_batch
                del chunk

            metadata = assembly.complete()

            return await upload.complete(
                duration_seconds=metadata.duration_seconds,
                turn_timings=metadata.turn_timings,
            )
        except BaseException:
            with suppress(Exception):
                await upload.abort()

            raise
