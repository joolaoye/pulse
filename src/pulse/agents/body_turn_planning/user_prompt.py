USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete body-turn-planning requirements,
duration-weight semantics, conversational constraints, and output schema.

Using the finalized beat and available speaker profiles, produce the ordered
speaker-aware conversational turns needed to realize the beat.

Assign each turn an appropriate relative duration weight.

Treat the finalized beat as authoritative.

Produce only structured body-turn-planning output.
</task_definition>

<input>
{planning_context}
</input>
"""
