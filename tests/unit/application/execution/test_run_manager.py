from types import SimpleNamespace

import pytest

from pulse.application.execution.errors import WorkflowRunPipelineMismatchError
from pulse.application.execution.run_manager import RunManager
from pulse.types import (
    PodcastProfile,
    SpeakerProfile,
    SpeakerVoiceBinding,
    WorkflowOutcome,
)


def _pipeline():
    return SimpleNamespace(
        pipeline_id="pipeline-a",
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
        target_episode_duration_seconds=300,
    )


class _RuntimeFactory:
    def __init__(self) -> None:
        self.pipeline_ids: list[str] = []

    async def create(self, *, pipeline_id: str):
        self.pipeline_ids.append(pipeline_id)
        return SimpleNamespace(pipeline=_pipeline(), podcast_show=object())


class _Runner:
    def __init__(self, state: dict) -> None:
        self.state = state
        self.resume_calls = 0
        self.run_calls: list[dict] = []

    async def get_state(self) -> dict:
        return self.state

    async def resume(self) -> dict:
        self.resume_calls += 1
        return {"resumed": True}

    async def run(self, *, initial_state: dict) -> dict:
        self.run_calls.append(initial_state)
        return initial_state

    def close(self) -> None:
        return None


class _WorkflowFactory:
    def __init__(self, runner: _Runner) -> None:
        self.runner = runner
        self.run_ids: list[str] = []

    def create(self, *, run_id: str, runtime) -> _Runner:
        del runtime
        self.run_ids.append(run_id)
        return self.runner


def _manager(runner: _Runner) -> tuple[RunManager, _WorkflowFactory]:
    application = SimpleNamespace(podcast_pipeline_runtime_factory=_RuntimeFactory())
    manager = RunManager(application=application)
    workflow_factory = _WorkflowFactory(runner)
    manager._workflow_factory = workflow_factory
    return manager, workflow_factory


async def test_resume_rejects_a_different_pipeline() -> None:
    runner = _Runner(
        {
            "run_id": "run-1",
            "pipeline_id": "pipeline-a",
            "workflow_outcome": None,
        }
    )
    manager, workflow_factory = _manager(runner)

    with pytest.raises(WorkflowRunPipelineMismatchError):
        await manager.resume(run_id="run-1", pipeline_id="pipeline-b")

    assert workflow_factory.run_ids == ["run-1"]
    assert runner.resume_calls == 0
    assert runner.run_calls == []


async def test_resume_returns_a_completed_run_without_executing_it() -> None:
    completed = {
        "run_id": "run-1",
        "pipeline_id": "pipeline-a",
        "episode_id": "episode-1",
        "workflow_outcome": WorkflowOutcome.PUBLISHED,
    }
    runner = _Runner(completed)
    manager, _workflow_factory = _manager(runner)

    result = await manager.resume(run_id="run-1", pipeline_id="pipeline-a")

    assert result is completed
    assert result["workflow_outcome"] == WorkflowOutcome.PUBLISHED
    assert runner.resume_calls == 0
    assert runner.run_calls == []


async def test_run_or_resume_starts_the_supplied_run_when_no_checkpoint_exists() -> None:
    runner = _Runner({})
    manager, workflow_factory = _manager(runner)

    result = await manager.run_or_resume(run_id="run-1", pipeline_id="pipeline-a")

    assert workflow_factory.run_ids == ["run-1"]
    assert runner.resume_calls == 0
    assert len(runner.run_calls) == 1
    assert runner.run_calls[0]["run_id"] == "run-1"
    assert result["run_id"] == "run-1"
