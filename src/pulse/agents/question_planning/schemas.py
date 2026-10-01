from typing import List

from pydantic import BaseModel, Field

from pulse.types import ConversationAngle, ProcessedSignal


class QuestionPlanningInput(BaseModel):
    beat_title: str = Field(
        ...,
        description=(
            "The finalized editorial title of the conversational beat for "
            "which discussion questions are being planned."
        ),
    )
    beat_purpose: str = Field(
        ...,
        description=(
            "The finalized purpose the conversational beat must accomplish. "
            "The generated questions should help the conversation realize "
            "this purpose without broadening or redefining it."
        ),
    )
    conversation_angle: ConversationAngle = Field(
        ...,
        description=(
            "The finalized editorial framing for the beat. Its perspective, "
            "central thesis, narrative hook, listener value, and tension "
            "should guide the questions generated for the discussion."
        ),
    )
    topic_signals: List[ProcessedSignal] = Field(
        ...,
        min_length=1,
        description=(
            "The approved generation-ready source signals that ground the "
            "beat. Generated questions must remain supported by this source "
            "material and must not introduce unsupported editorial scope."
        ),
    )
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        description=(
            "The exact speaking-time budget allocated to the conversational "
            "beat. The planner should use this constraint to keep the number "
            "and complexity of questions realistic for the available time."
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
            f"<conversation_angle>\n"
            f"{self.conversation_angle.to_llm_string()}\n"
            f"</conversation_angle>\n\n"
            f"<approved_signals>\n"
            f"{self._render_signals()}\n"
            f"</approved_signals>\n\n"
            f"<target_duration_seconds>\n"
            f"{self.target_duration_seconds}\n"
            f"</target_duration_seconds>"
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


class ConversationQuestionPlanningOutput(BaseModel):
    question: str = Field(
        ...,
        description=(
            "A single open-ended discussion question that helps advance the "
            "current beat's purpose through the selected conversation angle."
        ),
    )
    rationale: str = Field(
        ...,
        description=(
            "A concise explanation of how the question contributes to "
            "developing the beat's purpose or conversation angle."
        ),
    )


class QuestionPlanningOutput(BaseModel):
    questions: List[ConversationQuestionPlanningOutput] = Field(
        ...,
        min_length=1,
        description=(
            "The ordered questions selected to guide development of the "
            "conversational beat within its available duration."
        ),
    )
