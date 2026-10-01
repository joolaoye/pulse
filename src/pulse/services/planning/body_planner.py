from typing import Dict, List

from pulse.services.planning.body_outline_planner import BodyOutlinePlanner
from pulse.services.planning.segment_planner import SegmentPlanner
from pulse.types import (
    EpisodeBody,
    ProcessedSignal,
    Segment,
    ThemedSignalCluster,
)


class BodyPlanner:
    def __init__(
        self,
        *,
        body_outline_planner: BodyOutlinePlanner,
        segment_planner: SegmentPlanner,
    ) -> None:
        self.body_outline_planner = body_outline_planner
        self.segment_planner = segment_planner

    async def plan(
        self,
        *,
        themed_signal_clusters: List[ThemedSignalCluster],
        processed_signals: List[ProcessedSignal],
        target_body_duration_seconds: int,
    ) -> EpisodeBody:
        clusters_by_id = self._index_clusters(
            themed_signal_clusters=themed_signal_clusters,
        )

        signals_by_id = self._index_signals(
            processed_signals=processed_signals,
        )

        body_outline = await self.body_outline_planner.plan(
            themed_signal_clusters=themed_signal_clusters,
            processed_signals=processed_signals,
            target_body_duration_seconds=target_body_duration_seconds,
        )

        segments: List[Segment] = []

        for segment_outline in body_outline.segments:
            cluster = clusters_by_id.get(segment_outline.cluster_id)

            if cluster is None:
                raise ValueError(
                    "Body outline references unknown themed signal "
                    f"cluster ID '{segment_outline.cluster_id}'."
                )

            relevant_signals = self._resolve_cluster_signals(
                cluster=cluster,
                signals_by_id=signals_by_id,
            )

            segment = await self.segment_planner.plan(
                segment_outline=segment_outline,
                relevant_signals=relevant_signals,
                previous_segment=segments[-1] if segments else None,
            )

            segments.append(segment)

        episode_body = EpisodeBody(
            segments=segments,
        )

        self._validate_body_duration(
            episode_body=episode_body,
            target_body_duration_seconds=target_body_duration_seconds,
        )

        return episode_body

    @staticmethod
    def _index_clusters(
        *,
        themed_signal_clusters: List[ThemedSignalCluster],
    ) -> Dict[int, ThemedSignalCluster]:
        clusters_by_id: Dict[int, ThemedSignalCluster] = {}

        for cluster in themed_signal_clusters:
            if cluster.cluster_id in clusters_by_id:
                raise ValueError(f"Duplicate themed signal cluster ID '{cluster.cluster_id}'.")

            clusters_by_id[cluster.cluster_id] = cluster

        return clusters_by_id

    @staticmethod
    def _index_signals(
        *,
        processed_signals: List[ProcessedSignal],
    ) -> Dict[str, ProcessedSignal]:
        signals_by_id: Dict[str, ProcessedSignal] = {}

        for signal in processed_signals:
            if signal.signal_id in signals_by_id:
                raise ValueError(
                    f"Processed signals contain duplicate signal ID '{signal.signal_id}'."
                )

            signals_by_id[signal.signal_id] = signal

        return signals_by_id

    @staticmethod
    def _resolve_cluster_signals(
        *,
        cluster: ThemedSignalCluster,
        signals_by_id: Dict[str, ProcessedSignal],
    ) -> List[ProcessedSignal]:
        unknown_signal_ids = [
            signal_id for signal_id in cluster.signal_ids if signal_id not in signals_by_id
        ]

        if unknown_signal_ids:
            raise ValueError(
                f"Themed signal cluster {cluster.cluster_id} references "
                f"unknown signal IDs: {unknown_signal_ids}."
            )

        return [signals_by_id[signal_id] for signal_id in cluster.signal_ids]

    @staticmethod
    def _validate_body_duration(
        *,
        episode_body: EpisodeBody,
        target_body_duration_seconds: int,
    ) -> None:
        if episode_body.total_duration_seconds != target_body_duration_seconds:
            raise ValueError(
                "Episode body segment durations do not match the requested body duration."
            )
