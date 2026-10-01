from pulse.infrastructure.prompting import PromptBuilder

EXAMPLES = [
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.GOOD,
        user_input="""
        {
            "beat_title": "From Assistance to Delegation",
            "beat_purpose": "Establish how coding assistants are evolving from tools that help developers write code into systems that can take ownership of larger software engineering tasks.",
            "conversation_angle": {
                "title": "The Developer Becomes the Reviewer",
                "perspective": "Developer",
                "central_thesis": "As coding agents take ownership of larger implementation tasks, the developer's role increasingly shifts from producing every change directly to supervising, evaluating, and correcting autonomous work.",
                "narrative_hook": "The important change may not be that AI writes more code, but that developers are starting to hand over responsibility for entire pieces of engineering work.",
                "listener_value": "Listeners understand how greater agent autonomy changes the day-to-day role of software engineers rather than viewing the shift as simply another improvement in code generation.",
                "tension": "Delegating more implementation can increase developer leverage, but it also makes the ability to verify autonomous work increasingly important."
            },
            "topic_signals": [
                {
                    "signal_id": "1",
                    "source": "x",
                    "title": "Cursor introduces autonomous coding workflows",
                    "markdown_context": "Cursor introduced autonomous coding workflows that allow developers to delegate increasingly complex software engineering tasks to AI."
                },
                {
                    "signal_id": "2",
                    "source": "x",
                    "title": "Windsurf expands autonomous software engineering agents",
                    "markdown_context": "Windsurf expanded agentic coding capabilities so AI systems can work across larger software engineering tasks with less direct developer intervention."
                }
            ],
            "target_duration_seconds": 120
        }
        """.strip(),
        assistant_response="""
        {
            "questions": [
                {
                    "question": "What changes in a developer's job when the AI is responsible for completing an engineering task rather than simply helping write the code?",
                    "rationale": "Establishes the core transition from direct implementation to supervision that the beat is intended to explain."
                },
                {
                    "question": "As developers delegate larger tasks, which parts of engineering judgment become more important rather than less important?",
                    "rationale": "Develops the chosen developer perspective by examining the human responsibilities that remain important as implementation becomes more autonomous."
                },
                {
                    "question": "How does the need to review and verify autonomous work change the productivity tradeoff created by greater delegation?",
                    "rationale": "Explores the tension between increased leverage and the growing importance of evaluating the agent's work."
                }
            ]
        }
        """.strip(),
        user_feedback=(
            "Excellent. Three questions are appropriate for the available duration, "
            "each develops a distinct part of the beat, and the sequence moves from "
            "role change to human judgment to the central delegation-versus-verification "
            "tension without broadening the beat."
        ),
    ),
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.GOOD,
        user_input="""
        {
            "beat_title": "General Intelligence Reaches the Warehouse",
            "beat_purpose": "Connect advances in general-purpose robot intelligence with the growing possibility of deploying humanoid robots across practical warehouse and logistics tasks.",
            "conversation_angle": {
                "title": "The Bottleneck Moves From Programming to Deployment",
                "perspective": "Enterprise",
                "central_thesis": "As robot intelligence becomes more general-purpose, the competitive challenge increasingly shifts from programming a robot for one task to making adaptable systems reliable enough for real operating environments.",
                "narrative_hook": "If a robot no longer needs to be engineered from scratch for every warehouse task, the harder question becomes whether businesses can trust it on the floor.",
                "listener_value": "Listeners understand why increasingly general robot intelligence could change both the economics and the practical requirements of warehouse automation.",
                "tension": "More adaptable intelligence can reduce task-specific engineering, but practical adoption still depends on whether that flexibility translates into reliable real-world performance."
            },
            "topic_signals": [
                {
                    "signal_id": "4",
                    "source": "x",
                    "title": "Figure demonstrates humanoid robots performing warehouse tasks",
                    "markdown_context": "Figure demonstrated humanoid robots performing increasingly complex warehouse and logistics tasks with reduced human intervention."
                },
                {
                    "signal_id": "5",
                    "source": "x",
                    "title": "Physical Intelligence launches robotics foundation model",
                    "markdown_context": "Physical Intelligence introduced a foundation model designed to support general-purpose robotic manipulation across different tasks and environments."
                }
            ],
            "target_duration_seconds": 75
        }
        """.strip(),
        assistant_response="""
        {
            "questions": [
                {
                    "question": "Why does more general-purpose robot intelligence make warehouses a more realistic deployment environment than when robots must be engineered for individual tasks?",
                    "rationale": "Connects the technical advance directly to the practical deployment implication at the center of the beat."
                },
                {
                    "question": "If programming each task becomes less of the bottleneck, what still has to be proven before businesses can rely on these robots in real operations?",
                    "rationale": "Uses the selected enterprise tension to move from capability to the remaining challenge of dependable deployment."
                }
            ]
        }
        """.strip(),
        user_feedback=(
            "Excellent. The shorter duration produces only two focused questions. "
            "They cover the essential movement from general-purpose capability to "
            "deployment reliability without introducing unrelated robotics topics."
        ),
    ),
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.AMBIGUOUS,
        user_input="""
        {
            "beat_title": "Evaluation Catches Up With Autonomy",
            "beat_purpose": "Explain why increasingly autonomous coding agents make evaluation against complete, realistic engineering workflows more important than measuring isolated coding ability.",
            "conversation_angle": {
                "title": "The Benchmark Has to Measure Responsibility",
                "perspective": "Technology",
                "central_thesis": "Once coding agents are expected to complete substantial engineering workflows autonomously, useful evaluation must measure whether they can reliably carry responsibility across the workflow rather than simply produce correct code in isolation.",
                "narrative_hook": "A system can look impressive on individual coding tasks and still fail at the kind of sustained engineering work developers actually want to delegate.",
                "listener_value": "Listeners understand why greater agent autonomy changes what meaningful coding-agent evaluation needs to measure.",
                "tension": "The more responsibility developers delegate to an agent, the less useful narrow capability scores become as evidence that the agent can be trusted with the full task."
            },
            "topic_signals": [
                {
                    "signal_id": "3",
                    "source": "x",
                    "title": "Anthropic releases benchmark for coding agents",
                    "markdown_context": "Anthropic released evaluation work focused on measuring the ability of AI coding agents to perform realistic software engineering tasks. Community discussion emphasized that reliability becomes more important as agents take responsibility for larger workflows."
                }
            ],
            "target_duration_seconds": 180
        }
        """.strip(),
        assistant_response="""
        {
            "questions": [
                {
                    "question": "What does a complete engineering workflow test that an isolated coding task cannot?",
                    "rationale": "Establishes the core distinction the beat needs the listener to understand."
                },
                {
                    "question": "Why does greater agent autonomy make reliability across the entire workflow more important than isolated demonstrations of coding ability?",
                    "rationale": "Connects the change in evaluation directly to the increase in responsibility being delegated to the agent."
                },
                {
                    "question": "What kinds of failures become more consequential when an agent is expected to carry a task through multiple stages rather than produce one correct answer?",
                    "rationale": "Deepens the discussion by examining why sustained responsibility creates a different evaluation problem."
                },
                {
                    "question": "At what point does a benchmark become evidence that developers can actually trust an agent with real engineering work rather than evidence that the model is merely capable?",
                    "rationale": "Develops the central tension between demonstrated capability and trustworthy delegation while remaining within the beat's evaluation focus."
                }
            ]
        }
        """.strip(),
        user_feedback=(
            "Strong editorial judgment. The longer duration supports a deeper four-step "
            "discussion, and the questions progress from defining the evaluation gap "
            "to autonomy, failure modes, and trust without drifting into a broader "
            "conversation about AI coding careers or products."
        ),
    ),
]
