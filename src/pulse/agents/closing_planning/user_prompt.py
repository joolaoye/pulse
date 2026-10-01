USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete closing-planning requirements,
editorial principles, duration constraints, and output schema.

Using the provided finalized episode body and closing duration budget, design
the editorial plan for the episode closing.

Determine:

1. The episode-specific closing objective.

2. The most appropriate resolution strategy.

3. The single final takeaway listeners should retain.

4. The closing goal describing how the conversation should naturally come to
   rest after the final substantive beat of the final segment.

Treat the episode body as authoritative.

Use the target duration to constrain the scope and complexity of the closing.

Produce only the structured closing-planning output.
</task_definition>

<input>
{planning_context}
</input>
"""
