from typing import List

from pydantic import BaseModel, Field

from pulse.types import ProcessedSignal


class ConversationAnglePlanningInput(BaseModel):
    beat_title: str = Field(
        ...,
        description=(
            "The finalized editorial title of the conversational beat being "
            "developed. It identifies the specific conversational movement "
            "whose framing the conversation angle must support."
        ),
    )
    beat_purpose: str = Field(
        ...,
        description=(
            "The finalized purpose of the conversational beat. It defines what "
            "the discussion must establish, explain, connect, contrast, or "
            "interpret before advancing. The conversation angle must help "
            "realize this purpose without broadening or redefining it."
        ),
    )
    topic_signals: List[ProcessedSignal] = Field(
        ...,
        min_length=1,
        description=(
            "The approved generation-ready source signals that ground the "
            "conversational beat. They provide the factual evidence available "
            "for developing the conversation angle and must not be expanded "
            "with additional source material."
        ),
    )

    def to_llm_string(self) -> str:
        return (
            f"<beat_title>\n"
            f"{self.beat_title}\n"
            f"</beat_title>\n\n"
            f"<beat_purpose>\n"
            f"{self.beat_purpose}\n"
            f"</beat_purpose>\n\n"
            f"<approved_signals>\n"
            f"{self._render_signals()}\n"
            f"</approved_signals>"
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


class ConversationAnglePlanningOutput(BaseModel):
    title: str = Field(
        ...,
        description=("A concise editorial title describing the conversation angle for the beat."),
    )
    perspective: str = Field(
        ...,
        description=("The primary lens through which the beat should be explored."),
    )
    central_thesis: str = Field(
        ...,
        description=(
            "A single opinionated but source-grounded statement around which "
            "the conversation should revolve."
        ),
    )
    narrative_hook: str = Field(
        ...,
        description=(
            "The editorial idea that should create immediate listener "
            "curiosity when the beat begins. This is planning guidance, not "
            "scripted dialogue."
        ),
    )
    listener_value: str = Field(
        ...,
        description=(
            "What the listener should understand, learn, or gain from "
            "experiencing the beat through this conversation angle."
        ),
    )
    tension: str = Field(
        ...,
        description=(
            "The source-grounded uncertainty, tradeoff, conflict, or open "
            "question that gives the beat conversational momentum."
        ),
    )
