from datetime import datetime
from typing import Dict, List, Optional, Required, TypedDict

from pulse.types import (
    Discourse,
    EmbeddedSignal,
    EpisodeMetadata,
    EpisodeScript,
    NoContentReason,
    PodcastProfile,
    PodcastShow,
    ProcessedSignal,
    PublicationResult,
    Signal,
    SpeakerProfile,
    SpeakerVoiceBinding,
    StoredEpisodeAudio,
    ThemedSignalCluster,
    TurnPlan,
    WorkflowOutcome,
)


class WorkflowState(
    TypedDict,
    total=False,
):
    # Inputs
    run_id: Required[str]
    pipeline_id: Required[str]
    episode_id: Required[str]
    published_at: Required[datetime]

    podcast_profile: Required[PodcastProfile]
    speakers: Required[List[SpeakerProfile]]
    speaker_voice_bindings: Required[List[SpeakerVoiceBinding]]
    target_episode_duration_seconds: Required[int]
    podcast_show: Required[PodcastShow]

    # Retrieval
    discourses: List[Discourse]

    # Ingestion
    unseen_signals: List[Signal]

    # Semantic processing
    embedded_signals_by_id: Dict[str, EmbeddedSignal]

    # Post-processing
    processed_signals_by_id: Dict[str, ProcessedSignal]

    # Grouping
    themed_signal_clusters: List[ThemedSignalCluster]

    # Planning
    turn_plan: TurnPlan

    # Scripting
    episode_script: EpisodeScript

    # Finalization
    episode_metadata: EpisodeMetadata
    stored_episode_audio: StoredEpisodeAudio

    # Publishing
    publication_result: PublicationResult

    # Completion
    workflow_outcome: Optional[WorkflowOutcome]
    no_content_reason: Optional[NoContentReason]
