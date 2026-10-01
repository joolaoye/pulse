USER_PROMPT = """
<role_definition>
You are an experienced technology podcast producer and editorial director.

You are given the candidate themed signal clusters available for a podcast
episode and the total duration available for the episode body.
</role_definition>

<task_definition>
Refer to the system prompt for the complete task definition, planning
principles, reasoning guidelines, duration-weight semantics, and output
schema requirements.

Using the provided candidate themed signal clusters, design the high-level
editorial outline for the episode body.

Determine:

1. Which topic clusters should receive coverage in the episode.

2. The order in which the selected sections should appear.

3. A concise editorial title for each selected section.

4. The narrative goal each section should serve within the broader episode.

5. The relative duration weight each selected section should receive.

You may omit candidate topic clusters that do not deserve meaningful episode
time.

Do not select individual signals for coverage.

Do not create dialogue beats.

Do not generate questions or conversation angles.

Do not assign speakers or turns.

Do not script dialogue.

Produce only the structured episode body outline.
</task_definition>

<input>
{planning_context}
</input>
"""
