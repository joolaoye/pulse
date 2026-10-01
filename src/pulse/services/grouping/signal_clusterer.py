import math
from typing import Dict, List, Optional, Tuple

from pulse.types import EmbeddedSignal, SignalCluster

DEFAULT_DISTANCE_THRESHOLD = 0.3
DEFAULT_METRIC = "cosine"
DEFAULT_LINKAGE = "average"

SUPPORTED_METRICS = {
    "cosine",
    "euclidean",
    "l2",
    "manhattan",
    "l1",
}

SUPPORTED_LINKAGES = {
    "average",
    "complete",
    "single",
}


class SignalClusterer:
    def __init__(
        self,
        *,
        metric: str = DEFAULT_METRIC,
        linkage: str = DEFAULT_LINKAGE,
        distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
    ) -> None:
        self.metric = metric
        self.linkage = linkage
        self.distance_threshold = distance_threshold

        self._validate_config()

    def cluster(
        self,
        embedded_signals: List[EmbeddedSignal],
    ) -> List[SignalCluster]:
        if not embedded_signals:
            return []

        if len(embedded_signals) == 1:
            return [
                SignalCluster(
                    cluster_id=0,
                    signal_ids=[embedded_signals[0].signal_id],
                )
            ]

        pairwise_distances = self._build_pairwise_distances(
            embeddings=[signal.embedding for signal in embedded_signals]
        )

        clusters: List[List[int]] = [[index] for index in range(len(embedded_signals))]

        while True:
            closest_pair = self._find_closest_clusters(
                clusters=clusters,
                pairwise_distances=pairwise_distances,
            )

            if closest_pair is None:
                break

            left_index, right_index, distance = closest_pair

            if distance >= self.distance_threshold:
                break

            clusters[left_index] += clusters[right_index]
            del clusters[right_index]

        clusters.sort(key=min)

        return [
            SignalCluster(
                cluster_id=cluster_id,
                signal_ids=[embedded_signals[index].signal_id for index in cluster],
            )
            for cluster_id, cluster in enumerate(clusters)
        ]

    def _validate_config(self) -> None:
        if self.metric not in SUPPORTED_METRICS:
            raise ValueError(f"Unsupported clustering metric: '{self.metric}'.")

        if self.linkage not in SUPPORTED_LINKAGES:
            raise ValueError(f"Unsupported clustering linkage: '{self.linkage}'.")

        if self.distance_threshold < 0:
            raise ValueError("Clustering distance threshold must be non-negative.")

    def _build_pairwise_distances(
        self,
        *,
        embeddings: List[List[float]],
    ) -> Dict[Tuple[int, int], float]:
        return {
            (left, right): self._distance(
                left=embeddings[left],
                right=embeddings[right],
            )
            for left in range(len(embeddings))
            for right in range(left + 1, len(embeddings))
        }

    def _find_closest_clusters(
        self,
        *,
        clusters: List[List[int]],
        pairwise_distances: Dict[Tuple[int, int], float],
    ) -> Optional[Tuple[int, int, float]]:
        closest_pair: Optional[Tuple[int, int, float]] = None

        for left in range(len(clusters)):
            for right in range(left + 1, len(clusters)):
                distance = self._cluster_distance(
                    left_cluster=clusters[left],
                    right_cluster=clusters[right],
                    pairwise_distances=pairwise_distances,
                )

                if closest_pair is None or distance < closest_pair[2]:
                    closest_pair = (
                        left,
                        right,
                        distance,
                    )

        return closest_pair

    def _cluster_distance(
        self,
        *,
        left_cluster: List[int],
        right_cluster: List[int],
        pairwise_distances: Dict[Tuple[int, int], float],
    ) -> float:
        distances = [
            self._get_pairwise_distance(
                left_index=left,
                right_index=right,
                pairwise_distances=pairwise_distances,
            )
            for left in left_cluster
            for right in right_cluster
        ]

        if self.linkage == "single":
            return min(distances)

        if self.linkage == "complete":
            return max(distances)

        return sum(distances) / len(distances)

    @staticmethod
    def _get_pairwise_distance(
        *,
        left_index: int,
        right_index: int,
        pairwise_distances: Dict[Tuple[int, int], float],
    ) -> float:
        if left_index == right_index:
            return 0.0

        key = (left_index, right_index) if left_index < right_index else (right_index, left_index)

        return pairwise_distances[key]

    def _distance(
        self,
        *,
        left: List[float],
        right: List[float],
    ) -> float:
        if len(left) != len(right):
            raise ValueError("Clustering requires embeddings with equal dimensions.")

        if self.metric == "cosine":
            return 1.0 - self._cosine_similarity(
                left=left,
                right=right,
            )

        if self.metric in {"euclidean", "l2"}:
            return math.sqrt(
                sum(
                    (left_value - right_value) ** 2
                    for left_value, right_value in zip(left, right, strict=True)
                )
            )

        return sum(
            abs(left_value - right_value)
            for left_value, right_value in zip(left, right, strict=True)
        )

    @staticmethod
    def _cosine_similarity(
        *,
        left: List[float],
        right: List[float],
    ) -> float:
        dot_product = sum(
            left_value * right_value for left_value, right_value in zip(left, right, strict=True)
        )

        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))

        denominator = left_norm * right_norm

        if denominator == 0:
            return 0.0

        return dot_product / denominator
