USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete question-planning requirements,
conversation-design principles, examples, and output schema.

Using the provided beat, conversation angle, approved source signals, and
target duration, plan the ordered discussion questions for this beat.

Generate the smallest useful set of questions needed to develop the beat's
purpose through the selected conversation angle.

The beat purpose and conversation angle are authoritative.

Use the approved source signals as the factual boundary for the questions.

Use the target duration to constrain the number, breadth, and complexity of
questions.

Produce only the structured question-planning output.
</task_definition>

<input>
{planning_context}
</input>
"""
