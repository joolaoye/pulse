USER_PROMPT = """
<task_definition>
Refer to the system prompt for the complete task definition, shortlisting
principles, planning guidelines, few-shot examples, and output schema
requirements.

Using the provided episode segment outline and relevant signals, create the
ordered topic shortlist for this segment.

Determine:

1. Which editorial topics are necessary to accomplish the segment's narrative
   goal.

2. Which signal should serve as the primary factual and editorial anchor for
   each topic.

3. Which additional signals should support each topic when they materially
   strengthen the same editorial idea.

4. The editorial goal each topic should accomplish for the listener.

5. The relative duration weight each topic should receive compared with the
   other shortlisted topics.

Prefer the minimum set of strong, coherent topics needed to accomplish the
segment's narrative goal.

Produce only the structured topic shortlist.
</task_definition>

<input>
{planning_context}
</input>
"""
