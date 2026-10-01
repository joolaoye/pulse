USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete opening-planning requirements,
editorial principles, duration constraints, and output schema.

Using the provided finalized episode body and opening duration budget, design
the editorial plan for the episode opening.

Determine:

1. The episode-specific opening objective.

2. The most appropriate hook strategy.

3. How the podcast should be briefly established for the listener.

4. How the host and co-host should be naturally established before the main
   discussion begins.

5. The listener promise.

6. The transition goal into the first substantive beat of the first segment.

Treat the episode body as authoritative.

Use the target duration to constrain the scope and complexity of the opening.

Produce only the structured opening-planning output.
</task_definition>

<input>
{planning_context}
</input>
"""
