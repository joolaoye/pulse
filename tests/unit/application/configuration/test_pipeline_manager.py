import pytest

from pulse.application.configuration.errors import PodcastShowNotFoundError
from pulse.application.configuration.models import PodcastPipelineUpdate
from pulse.application.configuration.pipeline_manager import PipelineManager
from pulse.types import PodcastPipeline, PodcastProfile, SpeakerProfile, SpeakerVoiceBinding


def _pipeline(*, show_id: str = "show-1", x_list_id: str = "list-1842") -> PodcastPipeline:
    return PodcastPipeline(
        pipeline_id="pipeline-alpha",
        show_id=show_id,
        podcast_profile=PodcastProfile(
            name="Nightly Pulse",
            purpose="Explain rate moves for operators.",
            target_audience="Treasury leads",
            editorial_style="Specific and sourced",
            conversational_style="Direct",
        ),
        speakers=[
            SpeakerProfile(
                speaker_id="host",
                display_name="Mina Cho",
                podcast_role="Host",
                persona="Asks for the mechanism",
                expertise=["markets"],
                speaking_style="Short questions",
            )
        ],
        speaker_voice_bindings=[
            SpeakerVoiceBinding(speaker_id="host", voice_id="voice-host"),
        ],
        interest_profile_markdown="# Rates\n\nWhat the statement changed.",
        x_list_id=x_list_id,
        target_episode_duration_seconds=900,
        enabled=False,
    )


class _ShowRepository:
    def __init__(self, show_ids: set[str]) -> None:
        self.show_ids = show_ids

    async def get(self, *, show_id: str):
        if show_id in self.show_ids:
            return object()
        return None


class _PipelineRepository:
    def __init__(self) -> None:
        self.pipelines: dict[str, PodcastPipeline] = {}
        self.created: list[PodcastPipeline] = []
        self.updated: list[PodcastPipeline] = []

    async def get(self, *, pipeline_id: str) -> PodcastPipeline | None:
        return self.pipelines.get(pipeline_id)

    async def create(self, *, pipeline: PodcastPipeline) -> None:
        self.created.append(pipeline)
        self.pipelines[pipeline.pipeline_id] = pipeline

    async def update(self, *, pipeline: PodcastPipeline) -> None:
        self.updated.append(pipeline)
        self.pipelines[pipeline.pipeline_id] = pipeline


def _manager(
    *,
    show_ids: set[str],
    pipeline: PodcastPipeline | None = None,
) -> tuple[PipelineManager, _PipelineRepository]:
    repository = _PipelineRepository()
    if pipeline is not None:
        repository.pipelines[pipeline.pipeline_id] = pipeline
    manager = PipelineManager(
        podcast_pipeline_repository=repository,
        podcast_show_repository=_ShowRepository(show_ids),
    )
    return manager, repository


async def test_create_requires_an_existing_show() -> None:
    manager, repository = _manager(show_ids=set())

    with pytest.raises(PodcastShowNotFoundError):
        await manager.create(pipeline=_pipeline())

    assert repository.created == []


async def test_partial_update_preserves_omitted_configuration() -> None:
    original = _pipeline()
    manager, repository = _manager(show_ids={"show-1"}, pipeline=original)

    updated = await manager.update(
        pipeline_id=original.pipeline_id,
        update=PodcastPipelineUpdate(x_list_id="list-revised"),
    )

    assert updated.x_list_id == "list-revised"
    assert updated.show_id == original.show_id
    assert updated.podcast_profile == original.podcast_profile
    assert updated.speakers == original.speakers
    assert updated.speaker_voice_bindings == original.speaker_voice_bindings
    assert updated.interest_profile_markdown == original.interest_profile_markdown
    assert updated.target_episode_duration_seconds == original.target_episode_duration_seconds
    assert updated.enabled is False
    assert repository.updated == [updated]

    with pytest.raises(PodcastShowNotFoundError):
        await manager.update(
            pipeline_id=original.pipeline_id,
            update=PodcastPipelineUpdate(show_id="missing-show"),
        )

    stored = await repository.get(pipeline_id=original.pipeline_id)
    assert stored is not None
    assert stored.show_id == "show-1"
    assert stored.x_list_id == "list-revised"
