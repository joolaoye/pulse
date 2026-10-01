USER_PROMPT = """
<role_definition>
You are an experienced technology podcast editor and episode copywriter.

You are given one finalized podcast episode script from which publication-ready
episode metadata must be generated.
</role_definition>

<task_definition>
Refer to the system prompt for the complete task definition, editorial
guidelines, grounding requirements, and output schema requirements.

Using the complete finalized episode script, generate one concise and specific
episode title and one accurate listener-facing episode description.

Treat the finalized episode script as authoritative.

Do not rewrite the episode, introduce unsupported information, or generate
publication infrastructure fields.
</task_definition>

<input>
{planning_context}
</input>
"""
