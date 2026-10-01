from pulse.infrastructure.storage.r2 import (
    R2Client,
    create_audio_object_store,
)
from pulse.infrastructure.storage.repositories import AudioRepository
from pulse.infrastructure.tts.elevenlabs import ElevenLabsDialogueProvider
from pulse.services.audio import (
    AudioAssembler,
    AudioProducer,
    DialogueBatcher,
    DialogueSynthesizer,
)


def create_audio_producer(
    *,
    r2_client: R2Client,
    elevenlabs_dialogue_provider: ElevenLabsDialogueProvider,
    bucket_name: str,
    r2_bucket: object | None = None,
) -> AudioProducer:
    return AudioProducer(
        dialogue_batcher=DialogueBatcher(),
        dialogue_synthesizer=DialogueSynthesizer(
            dialogue_provider=elevenlabs_dialogue_provider,
        ),
        audio_assembler=AudioAssembler(),
        audio_repository=AudioRepository(
            object_store=create_audio_object_store(
                r2_client=r2_client,
                bucket_name=bucket_name,
                bucket=r2_bucket,
            ),
        ),
    )
