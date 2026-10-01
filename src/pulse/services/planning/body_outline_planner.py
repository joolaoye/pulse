from typing import Dict, List

from pulse.agents import (
    BodyOutlineCandidateCluster,
    BodyOutlinePlanningAgent,
    BodyOutlinePlanningInput,
    BodyOutlinePlanningOutput,
)
from pulse.services.planning.duration import allocate_weighted_durations
from pulse.types import (
    BodyOutline,
    ProcessedSignal,
    SegmentOutline,
    ThemedSignalCluster,
)


class BodyOutlinePlanner:
    def __init__(
        self,
        *,
        body_outline_planning_agent: BodyOutlinePlanningAgent,
    ) -> None:
        self.body_outline_planning_agent = body_outline_planning_agent

    async def plan(
        self,
        *,
        themed_signal_clusters: List[ThemedSignalCluster],
        processed_signals: List[ProcessedSignal],
        target_body_duration_seconds: int,
    ) -> BodyOutline:
        candidate_clusters = self._build_candidate_clusters(
            themed_signal_clusters=themed_signal_clusters,
            processed_signals=processed_signals,
        )

        output = await self.body_outline_planning_agent.arun(
            BodyOutlinePlanningInput(
                candidate_clusters=candidate_clusters,
                target_body_duration_seconds=target_body_duration_seconds,
            )
        )

        self._validate_planning_output(
            output=output,
            candidate_clusters=candidate_clusters,
        )

        allocated_durations = allocate_weighted_durations(
            weights=[segment.duration_weight for segment in output.segments],
            target_duration_seconds=target_body_duration_seconds,
        )

        return BodyOutline(
            segments=[
                SegmentOutline(
                    cluster_id=segment.cluster_id,
                    title=segment.title,
                    narrative_goal=segment.narrative_goal,
                    target_duration_seconds=duration,
                )
                for segment, duration in zip(
                    output.segments,
                    allocated_durations,
                    strict=True,
                )
            ]
        )

    @staticmethod
    def _build_candidate_clusters(
        *,
        themed_signal_clusters: List[ThemedSignalCluster],
        processed_signals: List[ProcessedSignal],
    ) -> List[BodyOutlineCandidateCluster]:
        signals_by_id: Dict[str, ProcessedSignal] = {
            signal.signal_id: signal for signal in processed_signals
        }

        cluster_ids = [cluster.cluster_id for cluster in themed_signal_clusters]

        if len(cluster_ids) != len(set(cluster_ids)):
            raise ValueError("Themed signal clusters contain duplicate cluster IDs.")

        candidates = []

        for cluster in themed_signal_clusters:
            missing_signal_ids = [
                signal_id for signal_id in cluster.signal_ids if signal_id not in signals_by_id
            ]

            if missing_signal_ids:
                raise ValueError(
                    f"Cluster {cluster.cluster_id} references unknown "
                    f"signal IDs: {missing_signal_ids}."
                )

            candidates.append(
                BodyOutlineCandidateCluster(
                    cluster_id=cluster.cluster_id,
                    relevance_score=cluster.relevance_score,
                    theme=cluster.theme,
                    signals=[signals_by_id[signal_id] for signal_id in cluster.signal_ids],
                )
            )

        return candidates

    @staticmethod
    def _validate_planning_output(
        *,
        output: BodyOutlinePlanningOutput,
        candidate_clusters: List[BodyOutlineCandidateCluster],
    ) -> None:
        selected_cluster_ids = [segment.cluster_id for segment in output.segments]

        if len(selected_cluster_ids) != len(set(selected_cluster_ids)):
            raise ValueError("Body outline planning output contains duplicate cluster IDs.")

        known_cluster_ids = {cluster.cluster_id for cluster in candidate_clusters}

        unknown_cluster_ids = [
            cluster_id for cluster_id in selected_cluster_ids if cluster_id not in known_cluster_ids
        ]

        if unknown_cluster_ids:
            raise ValueError(
                "Body outline planning output references unknown "
                f"cluster IDs: {unknown_cluster_ids}."
            )
