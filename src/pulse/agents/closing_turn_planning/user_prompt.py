USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete turn-planning requirements,
duration-weight semantics, editorial constraints, and output schema.

Using the finalized episode closing, final segment, and available speaker
profiles, produce the ordered speaker-aware conversational turns needed to
realize the closing.

Use the final segment as context for where the closing begins, with particular
attention to its final beat as the immediate conversational predecessor.

Assign each planned turn an appropriate relative duration weight.

Treat the finalized episode closing as authoritative.

Produce only structured closing-turn-planning output.
</task_definition>

<input>
{planning_context}
</input>
"""
