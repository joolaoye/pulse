from typing import List, Optional

from pulse.services.planning.beat_planner import BeatPlanner
from pulse.services.planning.duration import allocate_weighted_durations
from pulse.services.planning.shortlist_planner import ShortlistPlanner
from pulse.types import (
    ProcessedSignal,
    Segment,
    SegmentOutline,
)


class SegmentPlanner:
    def __init__(
        self,
        *,
        shortlist_planner: ShortlistPlanner,
        beat_planner: BeatPlanner,
    ) -> None:
        self.shortlist_planner = shortlist_planner
        self.beat_planner = beat_planner

    async def plan(
        self,
        *,
        segment_outline: SegmentOutline,
        relevant_signals: List[ProcessedSignal],
        previous_segment: Optional[Segment] = None,
    ) -> Segment:
        shortlist = await self.shortlist_planner.plan(
            segment_outline=segment_outline,
            relevant_signals=relevant_signals,
        )

        beat_durations = allocate_weighted_durations(
            weights=[topic.duration_weight for topic in shortlist.topics],
            target_duration_seconds=segment_outline.target_duration_seconds,
        )

        beats = []
        previous_beat = previous_segment.beats[-1] if previous_segment else None

        for topic, target_duration_seconds in zip(
            shortlist.topics,
            beat_durations,
            strict=True,
        ):
            beat = await self.beat_planner.plan(
                topic=topic,
                relevant_signals=relevant_signals,
                target_duration_seconds=target_duration_seconds,
                previous_beat=previous_beat,
            )

            beats.append(beat)
            previous_beat = beat

        return Segment(
            title=segment_outline.title,
            narrative_goal=segment_outline.narrative_goal,
            target_duration_seconds=segment_outline.target_duration_seconds,
            beats=beats,
        )
