from typing import Dict, List, TypedDict

from pulse.types import (
    Discourse,
    EmbeddedSignal,
    EpisodeMetadata,
    EpisodeScript,
    NoContentReason,
    ProcessedSignal,
    PublicationResult,
    Signal,
    StoredEpisodeAudio,
    ThemedSignalCluster,
    TurnPlan,
    WorkflowOutcome,
)


class RetrieveSourcesUpdate(TypedDict):
    discourses: List[Discourse]


class IngestSignalsUpdate(TypedDict):
    unseen_signals: List[Signal]


class ProcessSemanticsUpdate(TypedDict):
    embedded_signals_by_id: Dict[str, EmbeddedSignal]


class PostProcessSignalsUpdate(TypedDict):
    processed_signals_by_id: Dict[str, ProcessedSignal]


class GroupSignalsUpdate(TypedDict):
    themed_signal_clusters: List[ThemedSignalCluster]


class PlanEpisodeUpdate(TypedDict):
    turn_plan: TurnPlan


class GenerateScriptUpdate(TypedDict):
    episode_script: EpisodeScript


class GenerateEpisodeMetadataUpdate(TypedDict):
    episode_metadata: EpisodeMetadata


class ProduceAudioUpdate(TypedDict):
    stored_episode_audio: StoredEpisodeAudio


class PublishEpisodeUpdate(TypedDict):
    publication_result: PublicationResult


class CompleteWithoutEpisodeUpdate(TypedDict):
    workflow_outcome: WorkflowOutcome
    no_content_reason: NoContentReason


class CommitSignalsUpdate(TypedDict):
    workflow_outcome: WorkflowOutcome
