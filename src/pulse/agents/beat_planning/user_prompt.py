USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete beat-planning requirements and
output schema.

Using the provided topic, approved source signals, target duration, and
optional previous-beat context, plan one conversational beat.

Define:

1. A concise editorial title describing the conversational movement.

2. A concise purpose describing what the conversation must accomplish to
   realize the topic's editorial goal.

3. A segue transition when previous-beat context is provided.

The topic and its approved source material are authoritative.

Use the target duration to constrain the scope of the beat.

Use previous-beat context only to plan a natural entry into the current beat.

Produce only the structured beat-planning output.
</task_definition>

<input>
{planning_context}
</input>
"""
