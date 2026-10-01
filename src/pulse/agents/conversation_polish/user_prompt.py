USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete conversation-polish requirements,
semantic-preservation rules, continuity guidance, speaker-style requirements,
delivery-annotation rules, audio-readiness constraints, and output schema.

Polish the provided spoken turn.

Preserve the turn's substantive meaning, factual content, level of certainty,
and conversational function.

Use the previous polished spoken turn, when provided, only to improve the
immediate handoff and avoid unnecessary repetition.

Use the resolved speaker profile to keep the contribution natural and
consistent with the assigned speaker.

Apply only delivery annotations permitted by the runtime delivery instructions
defined in the system prompt.

Do not introduce new facts, examples, arguments, interpretations, jokes,
analogies, reactions, questions, or conclusions.

Do not substantially expand or contract the contribution.

Produce only structured ConversationPolishOutput.
</task_definition>

<input>
{planning_context}
</input>
"""
