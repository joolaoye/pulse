USER_PROMPT = """
<role_definition>
You are an expert technology analyst and trend researcher.

You are given a cluster of related signals.
</role_definition>

<task_definition>
Refer to the system prompt for the complete task definition, reasoning guidelines, and output schema requirements.

Analyze the provided signals and identify the underlying theme that best explains why they belong together.
</task_definition>

<input>
{signals_markdown}
</input>
"""
