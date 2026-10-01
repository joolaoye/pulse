from typing import List

from pydantic import BaseModel, Field

from pulse.types import (
    DURATION_WEIGHT_MAX,
    DURATION_WEIGHT_MIN,
    ProcessedSignal,
    SegmentOutline,
)


class ShortlistPlanningInput(BaseModel):
    segment_outline: SegmentOutline = Field(
        ...,
        description=(
            "The finalized high-level outline for the episode segment being "
            "planned. It defines the segment's editorial focus, narrative goal, "
            "and exact duration budget that should guide shortlisting."
        ),
    )
    relevant_signals: List[ProcessedSignal] = Field(
        ...,
        min_length=1,
        description=(
            "The processed signals available for consideration within this "
            "segment. Select and organize only material that meaningfully "
            "supports the segment outline."
        ),
    )

    def to_llm_string(self) -> str:
        relevant_signals_markdown = "\n\n---\n\n".join(
            self._render_signal(signal) for signal in self.relevant_signals
        )

        return (
            "# Segment Outline\n\n"
            f"{self.segment_outline.to_llm_string()}\n\n"
            "# Relevant Signals\n\n"
            f"{relevant_signals_markdown}"
        )

    @staticmethod
    def _render_signal(
        signal: ProcessedSignal,
    ) -> str:
        return (
            f"## Signal {signal.signal_id}\n\n"
            f"Signal ID:\n"
            f"{signal.signal_id}\n\n"
            f"Source:\n"
            f"{signal.source}\n\n"
            f"Relevance Score:\n"
            f"{signal.relevance_score:.3f}\n\n"
            f"Title:\n"
            f"{signal.title}\n\n"
            f"Context:\n"
            f"{signal.markdown_context}"
        )


class TopicPlanningOutput(BaseModel):
    primary_signal_id: str = Field(
        ...,
        min_length=1,
        description="The signal that provides the primary focus for this topic.",
    )
    supporting_signal_ids: List[str] = Field(
        default_factory=list,
        description=(
            "Additional signals that materially support or deepen the same "
            "topic without introducing a separate conversational focus."
        ),
    )
    editorial_goal: str = Field(
        ...,
        description=(
            "What discussing this topic should contribute toward accomplishing "
            "the segment's narrative goal."
        ),
    )
    duration_weight: int = Field(
        ...,
        ge=DURATION_WEIGHT_MIN,
        le=DURATION_WEIGHT_MAX,
        description=(
            "The relative amount of the segment's available discussion time "
            "this topic should receive compared with the other shortlisted topics."
        ),
    )


class ShortlistPlanningOutput(BaseModel):
    topics: List[TopicPlanningOutput] = Field(
        ...,
        min_length=1,
        description="The ordered topics shortlisted for discussion within the segment.",
    )
