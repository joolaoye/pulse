from typing import List, Optional

from pydantic import BaseModel, Field

from pulse.types import ProcessedSignal, Topic


class PreviousBeatContext(BaseModel):
    title: str = Field(
        ...,
        description=(
            "The editorial title of the immediately preceding beat. It gives "
            "the planner enough context to understand the conversational "
            "movement from which the current beat must continue."
        ),
    )
    purpose: str = Field(
        ...,
        description=(
            "The conversational purpose accomplished by the immediately "
            "preceding beat. It should be used only to plan a natural segue "
            "into the current beat."
        ),
    )


class BeatPlanningInput(BaseModel):
    topic: Topic = Field(
        ...,
        description=(
            "The finalized shortlisted topic that this beat must realize. "
            "Its selected signals, editorial goal, and relative emphasis are "
            "authoritative and must not be reconsidered."
        ),
    )
    topic_signals: List[ProcessedSignal] = Field(
        ...,
        min_length=1,
        description=(
            "The generation-ready source signals selected for this topic. "
            "These signals provide the factual grounding available for "
            "planning the beat and must not be expanded with other material."
        ),
    )
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        description=(
            "The exact speaking-time budget allocated to this beat, in "
            "seconds. The planner should use it to scope the conversational "
            "movement but must not modify or reproduce the duration."
        ),
    )
    previous_beat_context: Optional[PreviousBeatContext] = Field(
        default=None,
        description=(
            "A compact description of the immediately preceding beat when one "
            "exists. It is provided only so the planner can create a natural "
            "segue into the current beat. None indicates that the current beat "
            "is standalone and requires no segue transition."
        ),
    )

    def to_llm_string(self) -> str:
        return (
            f"<topic>\n"
            f"{self.topic.to_llm_string()}\n"
            f"</topic>\n\n"
            f"<approved_signals>\n"
            f"{self._render_signals()}\n"
            f"</approved_signals>\n\n"
            f"<target_duration_seconds>\n"
            f"{self.target_duration_seconds}\n"
            f"</target_duration_seconds>\n\n"
            f"<previous_beat_context>\n"
            f"{self._render_previous_beat_context()}\n"
            f"</previous_beat_context>"
        )

    def _render_signals(self) -> str:
        return "\n\n---\n\n".join(self._render_signal(signal) for signal in self.topic_signals)

    @staticmethod
    def _render_signal(signal: ProcessedSignal) -> str:
        return (
            f"## Signal {signal.signal_id}\n\n"
            f"Signal ID:\n"
            f"{signal.signal_id}\n\n"
            f"Source:\n"
            f"{signal.source}\n\n"
            f"Title:\n"
            f"{signal.title}\n\n"
            f"Context:\n"
            f"{signal.markdown_context}"
        )

    def _render_previous_beat_context(self) -> str:
        previous_beat_context = self.previous_beat_context

        if previous_beat_context is None:
            return "None"

        return (
            f"Previous Beat Title:\n"
            f"{previous_beat_context.title}\n\n"
            f"Previous Beat Purpose:\n"
            f"{previous_beat_context.purpose}"
        )


class BeatPlanningOutput(BaseModel):
    title: str = Field(
        ...,
        description=(
            "A concise editorial title describing the specific conversational "
            "movement through which the current topic should be developed. "
            "It should describe the progression of the discussion rather than "
            "repeat the topic's editorial goal or a source title."
        ),
    )
    purpose: str = Field(
        ...,
        description=(
            "A concise description of what this beat must establish, explain, "
            "connect, contrast, or interpret before the conversation can "
            "advance. It should operationalize the topic's editorial goal into "
            "one concrete conversational movement."
        ),
    )
    segue_transition: Optional[str] = Field(
        default=None,
        description=(
            "Planning guidance for naturally entering this beat from the "
            "immediately preceding beat. It should describe the conceptual "
            "bridge into the current beat without scripting exact dialogue. "
            "It must be None when no previous beat context is provided."
        ),
    )
