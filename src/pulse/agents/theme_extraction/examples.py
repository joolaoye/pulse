from pulse.infrastructure.prompting import PromptBuilder

EXAMPLES = [
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.GOOD,
        user_input="""
            {
                "signals": [
                    {
                        "title": "Cursor introduces autonomous coding workflows",
                        "markdown_context": "Cursor released new autonomous coding capabilities that allow developers to delegate increasingly complex programming tasks..."
                    },
                    {
                        "title": "Claude expands software engineering capabilities",
                        "markdown_context": "Anthropic announced improvements enabling Claude to perform larger software engineering workflows..."
                    },
                    {
                        "title": "Developers increasingly trust AI for implementation",
                        "markdown_context": "Community discussion suggests developers are delegating more implementation work to AI assistants..."
                    }
                ]
            }
            """.strip(),
        assistant_response="""
            {
                "title": "AI Coding Agents Become Autonomous Development Partners",
                "summary": "The signals collectively indicate a shift from AI-assisted programming toward autonomous software engineering, where AI systems increasingly perform larger portions of the development lifecycle with minimal human intervention."
            }
            """.strip(),
        user_feedback=(
            "Correctly identifies the broader technological trend instead of summarizing each individual signal."
        ),
    ),
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.GOOD,
        user_input="""
            {
                "signals": [
                    {
                        "title": "Y Combinator calls for AI-native service startups",
                        "markdown_context": "Y Combinator highlights opportunities to rebuild traditional service businesses using AI..."
                    },
                    {
                        "title": "Startups automate consulting with AI agents",
                        "markdown_context": "Founders are using AI agents to automate knowledge-intensive consulting workflows..."
                    },
                    {
                        "title": "Professional services increasingly become software",
                        "markdown_context": "Investors discuss the emergence of AI-first companies replacing labor-intensive services..."
                    }
                ]
            }
            """.strip(),
        assistant_response="""
            {
                "title": "AI-Native Service Companies Transform Traditional Industries",
                "summary": "The signals point to an emerging market trend where AI-native businesses are replacing or augmenting traditional service industries by productizing work that historically depended on human expertise."
            }
            """.strip(),
        user_feedback=(
            "Focuses on the broader market movement rather than describing individual companies."
        ),
    ),
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.AMBIGUOUS,
        user_input="""
            {
                "signals": [
                    {
                        "title": "OpenAI introduces new API pricing",
                        "markdown_context": "OpenAI announced updated pricing designed to support enterprise adoption..."
                    },
                    {
                        "title": "Anthropic releases Claude improvements",
                        "markdown_context": "Anthropic expanded Claude's capabilities for enterprise AI workflows..."
                    },
                    {
                        "title": "Google expands Gemini platform",
                        "markdown_context": "Google introduced additional Gemini features targeting enterprise developers..."
                    }
                ]
            }
            """.strip(),
        assistant_response="""
            {
                "title": "Competition Among Foundation Model Providers Intensifies",
                "summary": "Together, the signals indicate increasing competition among foundation model providers as they expand capabilities, pricing strategies, and platform offerings to strengthen enterprise adoption."
            }
            """.strip(),
        user_feedback=(
            "Chooses a specific competitive trend instead of using an overly broad theme such as 'Artificial Intelligence'."
        ),
    ),
]
