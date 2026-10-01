from typing import List, Set

from pulse.agents import (
    ShortlistPlanningAgent,
    ShortlistPlanningInput,
    ShortlistPlanningOutput,
)
from pulse.types import (
    ProcessedSignal,
    SegmentOutline,
    Shortlist,
    Topic,
)


class ShortlistPlanner:
    def __init__(
        self,
        *,
        shortlist_planning_agent: ShortlistPlanningAgent,
    ) -> None:
        self.shortlist_planning_agent = shortlist_planning_agent

    async def plan(
        self,
        *,
        segment_outline: SegmentOutline,
        relevant_signals: List[ProcessedSignal],
    ) -> Shortlist:
        available_signal_ids = self._get_available_signal_ids(
            relevant_signals=relevant_signals,
        )

        output = await self.shortlist_planning_agent.arun(
            ShortlistPlanningInput(
                segment_outline=segment_outline,
                relevant_signals=relevant_signals,
            )
        )

        self._validate_planning_output(
            output=output,
            available_signal_ids=available_signal_ids,
        )

        return Shortlist(
            topics=[
                Topic(
                    primary_signal_id=topic.primary_signal_id,
                    supporting_signal_ids=topic.supporting_signal_ids,
                    editorial_goal=topic.editorial_goal,
                    duration_weight=topic.duration_weight,
                )
                for topic in output.topics
            ]
        )

    @staticmethod
    def _get_available_signal_ids(
        *,
        relevant_signals: List[ProcessedSignal],
    ) -> Set[str]:
        signal_ids = [signal.signal_id for signal in relevant_signals]

        if len(signal_ids) != len(set(signal_ids)):
            raise ValueError("Relevant signals contain duplicate signal IDs.")

        return set(signal_ids)

    @staticmethod
    def _validate_planning_output(
        *,
        output: ShortlistPlanningOutput,
        available_signal_ids: Set[str],
    ) -> None:
        primary_signal_ids = [topic.primary_signal_id for topic in output.topics]

        if len(primary_signal_ids) != len(set(primary_signal_ids)):
            raise ValueError(
                "Shortlist planning output uses the same signal as primary for more than one topic."
            )

        for topic in output.topics:
            if topic.primary_signal_id not in available_signal_ids:
                raise ValueError(
                    "Shortlist planning output references unknown primary "
                    f"signal ID '{topic.primary_signal_id}'."
                )

            if topic.primary_signal_id in topic.supporting_signal_ids:
                raise ValueError(
                    "Shortlist planning output uses primary signal ID "
                    f"'{topic.primary_signal_id}' as a supporting signal "
                    "in the same topic."
                )

            if len(topic.supporting_signal_ids) != len(set(topic.supporting_signal_ids)):
                raise ValueError(
                    "Shortlist planning output contains duplicate supporting "
                    f"signal IDs for primary signal '{topic.primary_signal_id}'."
                )

            unknown_supporting_signal_ids = [
                signal_id
                for signal_id in topic.supporting_signal_ids
                if signal_id not in available_signal_ids
            ]

            if unknown_supporting_signal_ids:
                raise ValueError(
                    "Shortlist planning output references unknown supporting "
                    f"signal IDs {unknown_supporting_signal_ids} for primary "
                    f"signal '{topic.primary_signal_id}'."
                )
