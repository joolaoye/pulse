from typing import Dict, List

from pulse.agents.theme_extraction import (
    ThemeExtractionAgent,
    ThemeExtractionInput,
)
from pulse.services.grouping.signal_clusterer import SignalClusterer
from pulse.types import (
    EmbeddedSignal,
    ProcessedSignal,
    Theme,
    ThemedSignalCluster,
)

CLUSTER_RELEVANCE_TOP_N = 3


class SignalGroupBuilder:
    def __init__(
        self,
        *,
        signal_clusterer: SignalClusterer,
        theme_extraction_agent: ThemeExtractionAgent,
    ) -> None:
        self.signal_clusterer = signal_clusterer
        self.theme_extraction_agent = theme_extraction_agent

    async def build(
        self,
        *,
        embedded_signals: List[EmbeddedSignal],
        processed_signals: List[ProcessedSignal],
    ) -> List[ThemedSignalCluster]:
        if not embedded_signals:
            return []

        signals_by_id = self._index_signals(
            signals=processed_signals,
        )

        self._validate_alignment(
            embedded_signals=embedded_signals,
            signals_by_id=signals_by_id,
        )

        clusters = self.signal_clusterer.cluster(embedded_signals)

        groups: List[ThemedSignalCluster] = []

        for cluster in clusters:
            signals = [signals_by_id[signal_id] for signal_id in cluster.signal_ids]

            groups.append(
                ThemedSignalCluster(
                    cluster_id=cluster.cluster_id,
                    relevance_score=self._calculate_relevance(
                        signals=signals,
                    ),
                    theme=await self._extract_theme(
                        signals=signals,
                    ),
                    signal_ids=cluster.signal_ids,
                )
            )

        return groups

    async def _extract_theme(
        self,
        *,
        signals: List[ProcessedSignal],
    ) -> Theme:
        return await self.theme_extraction_agent.arun(
            ThemeExtractionInput(
                signals=signals,
            )
        )

    @staticmethod
    def _index_signals(
        *,
        signals: List[ProcessedSignal],
    ) -> Dict[str, ProcessedSignal]:
        signals_by_id: Dict[str, ProcessedSignal] = {}

        for signal in signals:
            if signal.signal_id in signals_by_id:
                raise ValueError(f"Duplicate processed signal ID '{signal.signal_id}'.")

            signals_by_id[signal.signal_id] = signal

        return signals_by_id

    @staticmethod
    def _validate_alignment(
        *,
        embedded_signals: List[EmbeddedSignal],
        signals_by_id: Dict[str, ProcessedSignal],
    ) -> None:
        embedded_ids = {signal.signal_id for signal in embedded_signals}

        if embedded_ids != set(signals_by_id):
            raise ValueError("Embedded and processed signals must contain the same signal IDs.")

    @staticmethod
    def _calculate_relevance(
        *,
        signals: List[ProcessedSignal],
    ) -> float:
        scores = sorted(
            (signal.relevance_score for signal in signals),
            reverse=True,
        )[:CLUSTER_RELEVANCE_TOP_N]

        return sum(scores) / len(scores)
