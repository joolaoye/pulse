USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete turn-scripting requirements,
planning-fidelity rules, duration constraints, grounding requirements,
continuity guidance, conversational guidelines, audio-readiness rules, and
output schema.

Using the finalized planned turn and the supplied resolved context, write the
exact spoken dialogue for this turn.

Treat the planned turn as authoritative.

Produce only structured TurnScriptingOutput.
</task_definition>

<input>
{planning_context}
</input>
"""
