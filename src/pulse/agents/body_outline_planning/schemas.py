from typing import List

from pydantic import BaseModel, Field

from pulse.types import (
    DURATION_WEIGHT_MAX,
    DURATION_WEIGHT_MIN,
    ProcessedSignal,
    Theme,
)


class BodyOutlineCandidateCluster(BaseModel):
    cluster_id: int
    relevance_score: float
    theme: Theme
    signals: List[ProcessedSignal] = Field(..., min_length=1)


class BodyOutlinePlanningInput(BaseModel):
    candidate_clusters: List[BodyOutlineCandidateCluster] = Field(
        ...,
        min_length=1,
        description=(
            "The candidate themed signal clusters available for the episode body. "
            "Compare them globally when deciding which clusters should become "
            "segments, how they should be ordered, and their relative emphasis."
        ),
    )
    target_body_duration_seconds: int = Field(
        ...,
        gt=0,
        description=(
            "The total episode-body duration available after opening and "
            "closing time have been reserved."
        ),
    )

    def to_llm_string(self) -> str:
        clusters = "\n\n---\n\n".join(
            self._render_cluster(index, cluster)
            for index, cluster in enumerate(
                self.candidate_clusters,
                start=1,
            )
        )

        return (
            f"<target_body_duration_seconds>\n"
            f"{self.target_body_duration_seconds}\n"
            f"</target_body_duration_seconds>\n\n"
            f"<themed_signal_clusters>\n"
            f"{clusters}\n"
            f"</themed_signal_clusters>"
        )

    @staticmethod
    def _render_cluster(
        index: int,
        cluster: BodyOutlineCandidateCluster,
    ) -> str:
        signal_lines = "\n".join(
            (f"- [{signal.signal_id}] (relevance={signal.relevance_score:.3f}) {signal.title}")
            for signal in cluster.signals
        )

        return (
            f"## Candidate Cluster {index}\n\n"
            f"Cluster ID:\n"
            f"{cluster.cluster_id}\n\n"
            f"Cluster Relevance:\n"
            f"{cluster.relevance_score:.3f}\n\n"
            f"{cluster.theme.to_llm_string()}\n\n"
            f"### Available Signals\n\n"
            f"{signal_lines}"
        )


class SegmentOutlinePlanningOutput(BaseModel):
    cluster_id: int = Field(
        ...,
        description=(
            "The identifier of the candidate themed signal cluster selected "
            "as the source for this episode segment. It must exactly match one "
            "of the cluster IDs provided in the planning input."
        ),
    )

    title: str = Field(
        ...,
        description=(
            "A concise editorial title for this episode segment. It should "
            "describe the segment's specific focus and role within the episode "
            "rather than simply restating the source cluster theme."
        ),
    )

    narrative_goal: str = Field(
        ...,
        description=(
            "A concise explanation of what this segment should accomplish in "
            "the overall episode narrative and what understanding, development, "
            "or takeaway it should establish for the listener."
        ),
    )

    duration_weight: int = Field(
        ...,
        ge=DURATION_WEIGHT_MIN,
        le=DURATION_WEIGHT_MAX,
        description=(
            "The relative amount of episode body time this segment should "
            "receive compared with the other selected segments. "
            f"{DURATION_WEIGHT_MIN} represents the lowest emphasis and "
            f"{DURATION_WEIGHT_MAX} represents the highest emphasis. "
            "This is a relative editorial weight, not a duration in seconds."
        ),
    )


class BodyOutlinePlanningOutput(BaseModel):
    segments: List[SegmentOutlinePlanningOutput] = Field(
        ...,
        min_length=1,
        description=(
            "The ordered episode segments selected from the available themed "
            "signal clusters. Their order defines the intended high-level "
            "narrative progression of the episode body. Candidate clusters "
            "that should not receive episode time should be omitted."
        ),
    )
