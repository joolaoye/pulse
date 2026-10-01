from pulse.infrastructure.prompting import PromptBuilder

EXAMPLES = [
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.GOOD,
        user_input="""
        {
            "beat_title": "From Assistance to Delegation",
            "beat_purpose": "Establish how coding assistants are evolving from tools that help developers write code into systems that can take ownership of larger software engineering tasks.",
            "topic_signals": [
                {
                    "signal_id": "1",
                    "source": "x",
                    "title": "Cursor introduces autonomous coding workflows",
                    "markdown_context": "Cursor introduced autonomous coding workflows that allow developers to delegate increasingly complex software engineering tasks to AI while remaining responsible for reviewing the resulting work."
                },
                {
                    "signal_id": "2",
                    "source": "x",
                    "title": "Windsurf expands autonomous software engineering agents",
                    "markdown_context": "Windsurf expanded its agentic coding capabilities, allowing AI systems to work across larger software engineering tasks with less direct developer intervention."
                }
            ]
        }
        """.strip(),
        assistant_response="""
        {
            "title": "The Developer Becomes the Reviewer",
            "perspective": "Developer",
            "central_thesis": "As coding agents take ownership of larger implementation tasks, the developer's role increasingly shifts from producing every change directly to supervising, evaluating, and correcting autonomous work.",
            "narrative_hook": "The important change may not be that AI writes more code, but that developers are starting to hand over responsibility for entire pieces of engineering work.",
            "listener_value": "Listeners understand how greater agent autonomy changes the day-to-day role of software engineers rather than viewing the shift as simply another improvement in code generation.",
            "tension": "Delegating more implementation can increase developer leverage, but it also makes the ability to verify autonomous work increasingly important."
        }
        """.strip(),
        user_feedback=(
            "Excellent. The angle remains within the beat's established purpose "
            "while choosing a concrete developer lens. It does not redesign the "
            "beat or merely repeat that coding agents are becoming more autonomous."
        ),
    ),
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.GOOD,
        user_input="""
        {
            "beat_title": "General Intelligence Reaches the Warehouse",
            "beat_purpose": "Connect advances in general-purpose robot intelligence with the growing possibility of deploying humanoid robots across practical warehouse and logistics tasks.",
            "topic_signals": [
                {
                    "signal_id": "4",
                    "source": "x",
                    "title": "Figure demonstrates humanoid robots performing warehouse tasks",
                    "markdown_context": "Figure demonstrated humanoid robots performing increasingly complex warehouse and logistics tasks with reduced human intervention, suggesting that warehouses may become an important early deployment environment."
                },
                {
                    "signal_id": "5",
                    "source": "x",
                    "title": "Physical Intelligence launches robotics foundation model",
                    "markdown_context": "Physical Intelligence introduced a foundation model designed to support general-purpose robotic manipulation across different tasks and environments, potentially reducing the need for task-specific robot programming."
                }
            ]
        }
        """.strip(),
        assistant_response="""
        {
            "title": "The Bottleneck Moves From Programming to Deployment",
            "perspective": "Enterprise",
            "central_thesis": "As robot intelligence becomes more general-purpose, the competitive challenge increasingly shifts from programming a robot for one task to making adaptable systems reliable enough for real operating environments.",
            "narrative_hook": "If a robot no longer needs to be engineered from scratch for every warehouse task, the harder question becomes whether businesses can trust it on the floor.",
            "listener_value": "Listeners understand why increasingly general robot intelligence could change both the economics and the practical requirements of warehouse automation.",
            "tension": "More adaptable intelligence can reduce task-specific engineering, but practical adoption still depends on whether that flexibility translates into reliable real-world performance."
        }
        """.strip(),
        user_feedback=(
            "Excellent. The framing connects the approved technical and deployment "
            "evidence through an enterprise lens without broadening the beat into a "
            "general discussion of robotics markets or investment."
        ),
    ),
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.AMBIGUOUS,
        user_input="""
        {
            "beat_title": "Evaluation Catches Up With Autonomy",
            "beat_purpose": "Explain why increasingly autonomous coding agents make evaluation against complete, realistic engineering workflows more important than measuring isolated coding ability.",
            "topic_signals": [
                {
                    "signal_id": "3",
                    "source": "x",
                    "title": "Anthropic releases benchmark for coding agents",
                    "markdown_context": "Anthropic released evaluation work focused on measuring the ability of AI coding agents to perform realistic software engineering tasks. Community discussion emphasized that reliability becomes more important as agents take responsibility for larger workflows."
                }
            ]
        }
        """.strip(),
        assistant_response="""
        {
            "title": "The Benchmark Has to Measure Responsibility",
            "perspective": "Technology",
            "central_thesis": "Once coding agents are expected to complete substantial engineering workflows autonomously, useful evaluation must measure whether they can reliably carry responsibility across the workflow rather than simply produce correct code in isolation.",
            "narrative_hook": "A system can look impressive on individual coding tasks and still fail at the kind of sustained engineering work developers actually want to delegate.",
            "listener_value": "Listeners understand why greater agent autonomy changes what meaningful coding-agent evaluation needs to measure.",
            "tension": "The more responsibility developers delegate to an agent, the less useful narrow capability scores become as evidence that the agent can be trusted with the full task."
        }
        """.strip(),
        user_feedback=(
            "Strong editorial judgment. Several framings are possible, but this "
            "angle stays tightly attached to the beat's purpose and identifies the "
            "deeper relationship between autonomy, responsibility, and evaluation "
            "without introducing a new topic."
        ),
    ),
]
