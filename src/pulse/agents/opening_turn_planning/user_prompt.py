USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete turn-planning requirements,
duration-weight semantics, editorial constraints, and output schema.

Using the finalized episode opening, first segment, and available speaker
profiles, produce the ordered speaker-aware conversational turns needed to
realize the opening.

Use the first segment as context for where the opening is going, with
particular attention to its first beat as the immediate conversational
destination.

Assign each planned turn an appropriate relative duration weight.

Produce only structured opening-turn-planning output.
</task_definition>

<input>
{planning_context}
</input>
"""
