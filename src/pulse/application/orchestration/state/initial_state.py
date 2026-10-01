from datetime import datetime

from pulse.application.orchestration.state import WorkflowState
from pulse.application.runtime import PodcastPipelineRuntime


def build_initial_workflow_state(
    *,
    runtime: PodcastPipelineRuntime,
    run_id: str,
    episode_id: str,
    published_at: datetime,
) -> WorkflowState:
    if not run_id.strip():
        raise ValueError("Workflow run ID cannot be empty.")

    if not episode_id.strip():
        raise ValueError("Episode ID cannot be empty.")

    return WorkflowState(
        pipeline_id=(runtime.pipeline.pipeline_id),
        run_id=run_id,
        episode_id=episode_id,
        published_at=published_at,
        podcast_profile=(runtime.pipeline.podcast_profile),
        speakers=(runtime.pipeline.speakers),
        speaker_voice_bindings=(runtime.pipeline.speaker_voice_bindings),
        target_episode_duration_seconds=(runtime.pipeline.target_episode_duration_seconds),
        podcast_show=(runtime.podcast_show),
        workflow_outcome=None,
        no_content_reason=None,
    )
