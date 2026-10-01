USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete conversation-angle planning
requirements, editorial principles, examples, and output schema.

Using the provided beat title, beat purpose, and approved source signals,
design the conversation angle that should guide this beat.

The beat title and purpose are authoritative.

Choose the strongest editorial framing that deepens the beat without
redefining its purpose or broadening its scope.

Produce only the structured conversation-angle output.
</task_definition>

<input>
{planning_context}
</input>
"""
