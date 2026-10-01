import pytest

from pulse.application.execution.errors import (
    PodcastPipelineDisabledError,
    PodcastPipelineNotFoundError,
)
from pulse.application.runtime.podcast_pipeline_runtime_factory import (
    PodcastPipelineRuntimeFactory,
)
from pulse.types import PodcastPipeline, PodcastProfile, SpeakerProfile, SpeakerVoiceBinding


def _pipeline(*, enabled: bool) -> PodcastPipeline:
    return PodcastPipeline(
        pipeline_id="pipeline-1",
        show_id="show-1",
        podcast_profile=PodcastProfile(
            name="Pulse",
            purpose="Explain the week's signals",
            target_audience="Builders",
            editorial_style="Specific",
            conversational_style="Direct",
        ),
        speakers=[
            SpeakerProfile(
                speaker_id="host",
                display_name="Host",
                podcast_role="Host",
                persona="Curious",
                speaking_style="Direct",
            )
        ],
        speaker_voice_bindings=[
            SpeakerVoiceBinding(speaker_id="host", voice_id="voice-1"),
        ],
        interest_profile_markdown="# Markets\n\nWhat changed this week.",
        x_list_id="list-1",
        target_episode_duration_seconds=300,
        enabled=enabled,
    )


class _PipelineRepository:
    def __init__(self, pipeline: PodcastPipeline | None) -> None:
        self.pipeline = pipeline

    async def get(self, *, pipeline_id: str) -> PodcastPipeline | None:
        del pipeline_id
        return self.pipeline


class _ShowRepository:
    def __init__(self, show: object | None) -> None:
        self.show = show

    async def get(self, *, show_id: str):
        del show_id
        return self.show


class _EmbeddingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, text: str) -> list[float]:
        del text
        self.calls += 1
        return [1.0]


def _factory(
    *,
    pipeline: PodcastPipeline | None,
    show: object | None = None,
    embedding_provider: _EmbeddingProvider | None = None,
) -> tuple[PodcastPipelineRuntimeFactory, _EmbeddingProvider]:
    provider = embedding_provider or _EmbeddingProvider()
    factory = PodcastPipelineRuntimeFactory(
        podcast_pipeline_repository=_PipelineRepository(pipeline),
        podcast_show_repository=_ShowRepository(show),
        d1_client=object(),
        vectorize_client=object(),
        embedding_provider=provider,
        x_retriever=object(),
        vectorize_index_name="signals",
    )
    return factory, provider


async def test_missing_pipeline_is_rejected_before_runtime_construction() -> None:
    factory, embedding_provider = _factory(pipeline=None)

    with pytest.raises(PodcastPipelineNotFoundError):
        await factory.create(pipeline_id="pipeline-1")

    assert embedding_provider.calls == 0


async def test_disabled_pipeline_is_rejected_before_runtime_construction() -> None:
    factory, embedding_provider = _factory(pipeline=_pipeline(enabled=False))

    with pytest.raises(PodcastPipelineDisabledError):
        await factory.create(pipeline_id="pipeline-1")

    assert embedding_provider.calls == 0


async def test_missing_show_is_rejected_before_runtime_construction() -> None:
    factory, embedding_provider = _factory(pipeline=_pipeline(enabled=True), show=None)

    with pytest.raises(ValueError):
        await factory.create(pipeline_id="pipeline-1")

    assert embedding_provider.calls == 0
