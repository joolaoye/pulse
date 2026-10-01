from typing import List, Optional

from pydantic import BaseModel, Field

DURATION_WEIGHT_MIN = 1
DURATION_WEIGHT_MAX = 5


def _format_signal_ids(signal_ids: List[str]) -> str:
    return ", ".join(signal_ids) if signal_ids else "None"


class SegmentOutline(BaseModel):
    cluster_id: int = Field(
        ...,
        description="The identifier of the themed signal cluster selected as the source for this episode segment. It maps the segment back to the candidate signals associated with that cluster.",
    )
    title: str = Field(
        ...,
        description="A concise editorial title describing this episode segment's focus and specific role rather than simply repeating the source cluster theme.",
    )
    narrative_goal: str = Field(
        ...,
        description="What this segment should accomplish in the broader episode narrative, including the perspective, development, tension, or takeaway it should establish for the listener.",
    )
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        description="The exact episode-body time allocated to this segment in seconds. This deterministic budget constrains downstream segment and beat planning.",
    )

    def to_llm_string(self) -> str:
        return (
            f"Segment Title:\n{self.title}\n\n"
            f"Cluster ID:\n{self.cluster_id}\n\n"
            f"Narrative Goal:\n{self.narrative_goal}\n\n"
            f"Target Duration:\n{self.target_duration_seconds} seconds"
        )


class BodyOutline(BaseModel):
    segments: List[SegmentOutline] = Field(
        ...,
        min_length=1,
        description="The ordered segment outlines selected for the episode body. Their order defines the body's high-level narrative progression, and each segment carries an exact downstream duration budget.",
    )

    @property
    def total_duration_seconds(self) -> int:
        return sum(segment.target_duration_seconds for segment in self.segments)

    def to_llm_string(self) -> str:
        return "\n\n---\n\n".join(
            f"# Episode Segment {index}\n\n{segment.to_llm_string()}"
            for index, segment in enumerate(self.segments, start=1)
        )


class ConversationAngle(BaseModel):
    title: str = Field(
        ...,
        description="A concise editorial title describing the conversation angle. It should capture the discussion's perspective rather than simply repeating the underlying theme.",
    )
    perspective: str = Field(
        ...,
        description="The primary lens through which the conversation should be explored, such as Developer, Founder, Investor, Enterprise, Research, Consumer, or Technology. Choose the most interesting perspective grounded in the provided theme.",
    )
    central_thesis: str = Field(
        ...,
        description="A single opinionated statement around which the conversation should revolve. It should synthesize the theme into a compelling claim without exaggerating or inventing facts.",
    )
    narrative_hook: str = Field(
        ...,
        description="The idea that should immediately capture listener curiosity at the beginning of the discussion. This is an editorial hook, not podcast dialogue.",
    )
    listener_value: str = Field(
        ...,
        description="Why this conversation matters to the listener and what they should understand, learn, or gain from hearing it.",
    )
    tension: str = Field(
        ...,
        description="The underlying uncertainty, tradeoff, conflict, or open question that gives the conversation momentum. It must emerge naturally from the provided evidence.",
    )

    def to_llm_string(self) -> str:
        return (
            "# Conversation Angle\n\n"
            f"Title:\n{self.title}\n\n"
            f"Perspective:\n{self.perspective}\n\n"
            f"Central Thesis:\n{self.central_thesis}\n\n"
            f"Narrative Hook:\n{self.narrative_hook}\n\n"
            f"Listener Value:\n{self.listener_value}\n\n"
            f"Tension:\n{self.tension}"
        )


class ConversationQuestion(BaseModel):
    question: str = Field(
        ...,
        description="A single open-ended question that develops an important part of the current conversational beat. It should be thought-provoking, grounded in approved evidence, consistent with the conversation angle, and suitable for discussion rather than a simple factual answer.",
    )
    rationale: str = Field(
        ...,
        description="Why this question is useful within the current beat and how it advances the beat's purpose or develops the selected conversation angle.",
    )

    def to_llm_string(self) -> str:
        return f"Question:\n{self.question}\n\nRationale:\n{self.rationale}"


class ConversationQuestions(BaseModel):
    questions: List[ConversationQuestion] = Field(
        ...,
        min_length=1,
        description="The ordered discussion questions planned for the conversational beat. Together they should guide development of the beat's purpose and angle without prescribing exact speaker turns or scripted dialogue.",
    )

    def to_llm_string(self) -> str:
        questions = "\n\n---\n\n".join(question.to_llm_string() for question in self.questions)
        return f"# Conversation Questions\n\n{questions}"


class Beat(BaseModel):
    primary_signal_id: str = Field(
        ...,
        description="The identifier of the signal serving as the primary factual anchor for this conversational beat. It is inherited from the shortlisted topic from which the beat was planned.",
    )
    supporting_signal_ids: List[str] = Field(
        default_factory=list,
        description="Identifiers of additional shortlisted signals that materially support this beat through evidence, context, contrast, consequence, or interpretation.",
    )
    title: str = Field(
        ...,
        description="A concise editorial title describing the specific conversational movement represented by this beat rather than simply repeating a source signal title or parent editorial goal.",
    )
    purpose: str = Field(
        ...,
        description="What this conversational beat must accomplish before the discussion advances. It operationalizes the parent topic's editorial goal by defining what the conversation must establish, explain, connect, contrast, or interpret.",
    )
    conversation_angle: ConversationAngle = Field(
        ...,
        description="The conversational framing used to develop this beat's purpose. It defines the perspective or approach without prescribing exact speaker turns or scripted wording.",
    )
    questions: ConversationQuestions = Field(
        ...,
        description="The planned questions that can drive the conversation toward accomplishing this beat's purpose and angle. They guide downstream turn planning without defining exact dialogue.",
    )
    segue_transition: Optional[str] = Field(
        default=None,
        description="Planning guidance for naturally entering this beat from the immediately preceding beat without scripting exact dialogue or introducing new editorial scope. None when there is no preceding beat.",
    )
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        description="The exact speaking time allocated to this beat in seconds, deterministically derived from the parent topic's relative duration weight within the segment's authoritative duration budget.",
    )

    def to_llm_string(self) -> str:
        segue_transition = self.segue_transition or "None"

        return (
            f"Title:\n{self.title}\n\n"
            f"Purpose:\n{self.purpose}\n\n"
            f"Primary Signal ID:\n{self.primary_signal_id}\n\n"
            f"Supporting Signal IDs:\n{_format_signal_ids(self.supporting_signal_ids)}\n\n"
            f"Conversation Angle:\n{self.conversation_angle.to_llm_string()}\n\n"
            f"Questions:\n{self.questions.to_llm_string()}\n\n"
            f"Segue Transition:\n{segue_transition}\n\n"
            f"Target Duration:\n{self.target_duration_seconds} seconds"
        )


class Segment(BaseModel):
    title: str = Field(
        ...,
        description="The editorial title of this major episode-body segment. It identifies the segment's specific focus without simply repeating the source cluster theme.",
    )
    narrative_goal: str = Field(
        ...,
        description="The high-level editorial purpose this segment should accomplish within the episode body and the understanding it should establish for the listener.",
    )
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        description="The exact amount of episode-body time allocated to this segment in seconds.",
    )
    beats: List[Beat] = Field(
        ...,
        min_length=1,
        description="The ordered conversational beats planned within this segment. Together they operationalize its narrative goal within the authoritative duration budget.",
    )

    @property
    def total_beat_duration_seconds(self) -> int:
        return sum(beat.target_duration_seconds for beat in self.beats)

    def to_llm_string(self) -> str:
        beats = "\n\n---\n\n".join(
            f"## Beat {index}\n\n{beat.to_llm_string()}"
            for index, beat in enumerate(self.beats, start=1)
        )

        return (
            "# Segment\n\n"
            f"Title:\n{self.title}\n\n"
            f"Narrative Goal:\n{self.narrative_goal}\n\n"
            f"Target Duration:\n{self.target_duration_seconds} seconds\n\n"
            f"# Beats\n\n{beats}"
        )


class Topic(BaseModel):
    primary_signal_id: str = Field(
        ...,
        description="The identifier of the signal serving as the primary factual and editorial anchor for this topic. It must reference one of the relevant signals available to the segment.",
    )
    supporting_signal_ids: List[str] = Field(
        default_factory=list,
        description="Identifiers of additional relevant signals that materially strengthen this topic through evidence, context, contrast, consequence, or interpretation.",
    )
    editorial_goal: str = Field(
        ...,
        description="What discussing this topic should contribute toward accomplishing the segment's narrative goal. It defines the editorial understanding to establish without prescribing questions, conversational structure, or spoken wording.",
    )
    duration_weight: int = Field(
        ...,
        ge=DURATION_WEIGHT_MIN,
        le=DURATION_WEIGHT_MAX,
        description=f"The relative amount of segment discussion time this topic deserves compared with the other shortlisted topics. {DURATION_WEIGHT_MIN} is the lowest emphasis and {DURATION_WEIGHT_MAX} the highest. This is an editorial weight, not a duration in seconds.",
    )

    def to_llm_string(self) -> str:
        return (
            f"Primary Signal ID:\n{self.primary_signal_id}\n\n"
            f"Supporting Signal IDs:\n{_format_signal_ids(self.supporting_signal_ids)}\n\n"
            f"Editorial Goal:\n{self.editorial_goal}\n\n"
            f"Duration Weight:\n{self.duration_weight}"
        )


class Shortlist(BaseModel):
    topics: List[Topic] = Field(
        ...,
        min_length=1,
        description="The ordered topics selected for discussion within the segment. Together they define the minimum source-grounded editorial material needed to accomplish the segment's narrative goal and the relative emphasis each topic should receive.",
    )

    def to_llm_string(self) -> str:
        return "\n\n---\n\n".join(
            f"# Topic {index}\n\n{topic.to_llm_string()}"
            for index, topic in enumerate(self.topics, start=1)
        )


class EpisodeBody(BaseModel):
    segments: List[Segment] = Field(
        ...,
        min_length=1,
        description="The ordered major segments that make up the substantive body of the episode.",
    )

    @property
    def total_duration_seconds(self) -> int:
        return sum(segment.target_duration_seconds for segment in self.segments)

    def to_llm_string(self) -> str:
        segments = "\n\n---\n\n".join(
            f"# Segment {index}\n\n{segment.to_llm_string()}"
            for index, segment in enumerate(self.segments, start=1)
        )
        return f"# Episode Body\n\n{segments}"


class EpisodeClosing(BaseModel):
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        description="The exact duration budget allocated to the episode closing. Downstream turn planning and scripting must realize the closing within this duration.",
    )
    objective: str = Field(
        ...,
        description="The primary purpose of the closing and what the ending should accomplish after the final episode beat has concluded.",
    )
    resolution_strategy: str = Field(
        ...,
        description="The editorial approach used to bring the episode to a satisfying conclusion, such as synthesizing the discussion, revisiting the central tension, broadening perspective, reframing the key insight, or ending with a reflective question. This describes the approach rather than dialogue.",
    )
    final_takeaway: str = Field(
        ...,
        description="The final supported observation, insight, or point of reflection that should remain with the listener. It does not need to summarize or unify the entire episode.",
    )
    closing_goal: str = Field(
        ...,
        description="How the conversation should conclude after the final episode beat, describing the desired ending experience without scripting narration or dialogue.",
    )

    def to_llm_string(self) -> str:
        return (
            f"Target Duration:\n{self.target_duration_seconds} seconds\n\n"
            f"Objective:\n{self.objective}\n\n"
            f"Resolution Strategy:\n{self.resolution_strategy}\n\n"
            f"Final Takeaway:\n{self.final_takeaway}\n\n"
            f"Closing Goal:\n{self.closing_goal}"
        )


class EpisodeOpening(BaseModel):
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        description="The exact duration budget allocated to the episode opening. Downstream turn planning and scripting must realize the opening within this duration.",
    )
    objective: str = Field(
        ...,
        description="The episode-specific editorial objective of the opening and what the listener should understand or feel before the main discussion begins.",
    )
    hook_strategy: str = Field(
        ...,
        description="The editorial approach used to capture listener attention without scripting the hook itself.",
    )
    podcast_introduction_goal: str = Field(
        ...,
        description="How the opening should briefly establish the podcast for the listener without scripting the exact introduction.",
    )
    speaker_introduction_goal: str = Field(
        ...,
        description="How the opening should naturally establish the host and co-host before the main discussion begins without assigning exact turns or scripting their introductions.",
    )
    listener_promise: str = Field(
        ...,
        description="The value proposition the opening should communicate and what the listener should expect to understand or gain by continuing with the episode.",
    )
    transition_goal: str = Field(
        ...,
        description="How the opening should naturally hand the conversation into the first episode beat without scripting the transition itself.",
    )

    def to_llm_string(self) -> str:
        return (
            f"Target Duration:\n{self.target_duration_seconds} seconds\n\n"
            f"Objective:\n{self.objective}\n\n"
            f"Hook Strategy:\n{self.hook_strategy}\n\n"
            f"Podcast Introduction Goal:\n{self.podcast_introduction_goal}\n\n"
            f"Speaker Introduction Goal:\n{self.speaker_introduction_goal}\n\n"
            f"Listener Promise:\n{self.listener_promise}\n\n"
            f"Transition Goal:\n{self.transition_goal}"
        )


class EpisodePlan(BaseModel):
    opening: EpisodeOpening
    body: EpisodeBody
    closing: EpisodeClosing

    @property
    def total_duration_seconds(self) -> int:
        return (
            self.opening.target_duration_seconds
            + self.body.total_duration_seconds
            + self.closing.target_duration_seconds
        )


class Turn(BaseModel):
    speaker_id: str = Field(
        ...,
        description="The stable identifier of the available speaker assigned to perform this conversational turn. It must correspond to one of the speaker profiles provided to the turn-planning agent.",
    )
    conversational_function: str = Field(
        ...,
        description="The primary conversational move this turn should perform, such as introducing an idea, asking a question, explaining evidence, challenging a claim, clarifying a point, giving an example, synthesizing discussion, or bridging into the next section.",
    )
    editorial_objective: str = Field(
        ...,
        description="The specific idea, question, or listener outcome this turn should advance, describing what the speaker must accomplish without scripting their exact words.",
    )
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        description="The exact speaking time allocated to this turn in seconds, deterministically derived from the authoritative duration budget of the parent opening, beat, or closing.",
    )

    def to_llm_string(self) -> str:
        return (
            f"Speaker ID:\n{self.speaker_id}\n\n"
            f"Conversational Function:\n{self.conversational_function}\n\n"
            f"Editorial Objective:\n{self.editorial_objective}\n\n"
            f"Target Duration:\n{self.target_duration_seconds} seconds"
        )


class OpeningTurnPlan(BaseModel):
    episode_opening: EpisodeOpening = Field(
        ...,
        description="The finalized episode-opening plan defining the objective, hook strategy, podcast introduction goal, speaker introduction goal, listener promise, transition goal, and authoritative duration constraint these turns must realize.",
    )
    turns: List[Turn] = Field(
        ...,
        min_length=1,
        description="The ordered speaker-aware conversational turns planned for the episode opening. Together they must realize the finalized opening strategy and naturally hand the conversation into the first substantive beat.",
    )

    @property
    def total_duration_seconds(self) -> int:
        return sum(turn.target_duration_seconds for turn in self.turns)

    def to_llm_string(self) -> str:
        turns = "\n\n".join(
            f"## Opening Turn {index}\n\n{turn.to_llm_string()}"
            for index, turn in enumerate(self.turns, start=1)
        )

        return (
            "# Episode Opening\n\n"
            f"{self.episode_opening.to_llm_string()}\n\n"
            "# Planned Opening Turns\n\n"
            f"{turns}"
        )


class ClosingTurnPlan(BaseModel):
    episode_closing: EpisodeClosing = Field(
        ...,
        description="The finalized episode-closing plan defining the objective, resolution strategy, final takeaway, closing goal, and authoritative duration budget these turns must realize.",
    )
    turns: List[Turn] = Field(
        ...,
        min_length=1,
        description="The ordered speaker-aware conversational turns planned for the episode closing. Together they must realize the finalized closing strategy within its authoritative duration budget.",
    )

    @property
    def total_duration_seconds(self) -> int:
        return sum(turn.target_duration_seconds for turn in self.turns)

    def to_llm_string(self) -> str:
        turns = "\n\n".join(
            f"## Closing Turn {index}\n\n{turn.to_llm_string()}"
            for index, turn in enumerate(self.turns, start=1)
        )

        return (
            "# Episode Closing\n\n"
            f"{self.episode_closing.to_llm_string()}\n\n"
            "# Planned Closing Turns\n\n"
            f"{turns}"
        )


class BeatTurnPlan(BaseModel):
    beat: Beat = Field(
        ...,
        description="The finalized conversational beat whose purpose, angle, questions, segue guidance, source selection, and exact duration budget are realized by the planned turns.",
    )
    turns: List[Turn] = Field(
        ...,
        min_length=1,
        description="The ordered speaker-aware conversational turns that realize the finalized beat within its authoritative duration budget.",
    )

    @property
    def total_duration_seconds(self) -> int:
        return sum(turn.target_duration_seconds for turn in self.turns)

    def to_llm_string(self) -> str:
        turns = "\n\n---\n\n".join(
            f"## Turn {index}\n\n{turn.to_llm_string()}"
            for index, turn in enumerate(self.turns, start=1)
        )

        return f"{self.beat.to_llm_string()}\n\n# Planned Turns\n\n{turns}"


class SegmentTurnPlan(BaseModel):
    segment: Segment = Field(
        ...,
        description="The finalized episode-body segment whose ordered beats are realized by the contained beat turn plans.",
    )
    beat_turn_plans: List[BeatTurnPlan] = Field(
        ...,
        min_length=1,
        description="The ordered turn plans for each finalized beat in the segment. Their ordering must preserve the beat ordering established by episode planning.",
    )

    @property
    def total_duration_seconds(self) -> int:
        return sum(beat_turn_plan.total_duration_seconds for beat_turn_plan in self.beat_turn_plans)

    def to_llm_string(self) -> str:
        beats = "\n\n---\n\n".join(
            f"## Beat Turn Plan {index}\n\n{beat_turn_plan.to_llm_string()}"
            for index, beat_turn_plan in enumerate(self.beat_turn_plans, start=1)
        )

        return f"{self.segment.to_llm_string()}\n\n# Planned Beat Turns\n\n{beats}"


class BodyTurnPlan(BaseModel):
    body: EpisodeBody = Field(
        ...,
        description="The finalized episode body whose segment and beat structure is realized by the contained speaker-aware turn plans.",
    )
    segment_turn_plans: List[SegmentTurnPlan] = Field(
        ...,
        min_length=1,
        description="The ordered speaker-aware turn plans for each finalized segment in the episode body. Their ordering must preserve the segment ordering established by episode planning.",
    )

    @property
    def total_duration_seconds(self) -> int:
        return sum(
            segment_turn_plan.total_duration_seconds
            for segment_turn_plan in self.segment_turn_plans
        )

    def to_llm_string(self) -> str:
        segments = "\n\n---\n\n".join(
            f"# Segment Turn Plan {index}\n\n{segment_turn_plan.to_llm_string()}"
            for index, segment_turn_plan in enumerate(
                self.segment_turn_plans,
                start=1,
            )
        )

        return f"# Episode Body Turn Plan\n\n{segments}"


class TurnPlan(BaseModel):
    opening: OpeningTurnPlan = Field(
        ...,
        description="The finalized speaker-aware turn plan for the episode opening.",
    )
    body: BodyTurnPlan = Field(
        ...,
        description="The finalized speaker-aware turn plan for the episode body, preserving the segment and beat hierarchy established by episode planning.",
    )
    closing: ClosingTurnPlan = Field(
        ...,
        description="The finalized speaker-aware turn plan for the episode closing.",
    )

    @property
    def total_duration_seconds(self) -> int:
        return (
            self.opening.total_duration_seconds
            + self.body.total_duration_seconds
            + self.closing.total_duration_seconds
        )

    def to_llm_string(self) -> str:
        return (
            "# Opening Turn Plan\n\n"
            f"{self.opening.to_llm_string()}\n\n"
            "---\n\n"
            "# Body Turn Plan\n\n"
            f"{self.body.to_llm_string()}\n\n"
            "---\n\n"
            "# Closing Turn Plan\n\n"
            f"{self.closing.to_llm_string()}"
        )
