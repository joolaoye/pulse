from pulse.infrastructure.prompting import PromptBuilder

EXAMPLES = [
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.GOOD,
        user_input="""
{
    "segment_outline": {
        "cluster_id": 7,
        "title": "The AI Chip Trade Breaks—and Who Bought the Dip",
        "narrative_goal": "Explain how leverage turned an AI-chip selloff into a forced unwind, why a better-capitalized counterparty could take the other side, and what the subsequent rebound reveals about the difference between a broken investment thesis and badly timed risk.",
        "target_duration_seconds": 420
    },
    "relevant_signals": [
        {
            "signal_id": "1",
            "source": "publication",
            "relevance_score": 0.97,
            "title": "Situational Awareness suffers major losses during the AI-chip selloff",
            "markdown_context": "Situational Awareness, founded by former OpenAI researcher Leopold Aschenbrenner, experienced significant losses as semiconductor and AI-related stocks declined sharply."
        },
        {
            "signal_id": "2",
            "source": "publication",
            "relevance_score": 0.95,
            "title": "Leverage forces an unwind of Situational Awareness's public-equity positions",
            "markdown_context": "Losses in the concentrated portfolio were amplified by leverage, ultimately forcing positions to be liquidated during the market decline."
        },
        {
            "signal_id": "3",
            "source": "publication",
            "relevance_score": 0.93,
            "title": "Citadel acquires AI-chip positions during the forced unwind",
            "markdown_context": "Citadel was able to take the other side of the distressed transaction and acquire positions being sold during the unwind."
        },
        {
            "signal_id": "4",
            "source": "publication",
            "relevance_score": 0.91,
            "title": "AI and semiconductor stocks rebound after the selloff",
            "markdown_context": "The semiconductor and AI-stock market subsequently recovered, lifting many of the same companies that had fallen during the earlier decline."
        }
    ]
}
""".strip(),
        assistant_response="""
{
    "topics": [
        {
            "primary_signal_id": "1",
            "supporting_signal_ids": [
                "2"
            ],
            "editorial_goal": "Establish how leverage transformed losses from the AI-chip selloff into a forced selling event, distinguishing ordinary market losses from the additional risk created by a concentrated leveraged position.",
            "duration_weight": 3
        },
        {
            "primary_signal_id": "3",
            "supporting_signal_ids": [
                "2"
            ],
            "editorial_goal": "Explain why the forced unwind created an opportunity for Citadel by contrasting an investor compelled to sell with a better-capitalized counterparty able to provide liquidity and acquire the positions.",
            "duration_weight": 2
        },
        {
            "primary_signal_id": "4",
            "supporting_signal_ids": [
                "1",
                "3"
            ],
            "editorial_goal": "Use the subsequent rebound to distinguish between the underlying AI-chip investment thesis and the risk of implementing that thesis with leverage, connecting the recovery to both the original losses and the opportunity created during the dislocation.",
            "duration_weight": 3
        }
    ]
}
""".strip(),
        user_feedback=(
            "Produces three coherent topics from four related signals rather "
            "than mechanically creating one topic per signal. The first topic "
            "establishes the leveraged unwind, the second isolates the "
            "counterparty opportunity, and the third develops the broader "
            "risk-versus-thesis takeaway. Relative duration weights give more "
            "development to the two ideas that carry the segment's main "
            "explanatory and interpretive work."
        ),
    ),
    PromptBuilder.FewShotExample(
        tag=PromptBuilder.ExampleTag.GOOD,
        user_input="""
{
    "segment_outline": {
        "cluster_id": 3,
        "title": "From Coding Assistant to Autonomous Engineer",
        "narrative_goal": "Establish how AI coding tools are moving from assisting developers with individual coding tasks toward owning increasingly complete software engineering workflows, and explain why that transition makes realistic evaluation more important.",
        "target_duration_seconds": 360
    },
    "relevant_signals": [
        {
            "signal_id": "11",
            "source": "x",
            "relevance_score": 0.96,
            "title": "Cursor introduces autonomous coding workflows",
            "markdown_context": "Cursor introduced workflows that allow developers to delegate increasingly complex implementation tasks to AI agents."
        },
        {
            "signal_id": "12",
            "source": "x",
            "relevance_score": 0.93,
            "title": "Windsurf expands autonomous software engineering agents",
            "markdown_context": "Windsurf expanded agentic capabilities across larger engineering tasks with less direct developer intervention."
        },
        {
            "signal_id": "13",
            "source": "publication",
            "relevance_score": 0.91,
            "title": "Anthropic releases benchmark for coding agents",
            "markdown_context": "Anthropic released evaluation work focused on measuring coding agents against realistic software engineering tasks rather than isolated code-generation problems."
        },
        {
            "signal_id": "14",
            "source": "publication",
            "relevance_score": 0.72,
            "title": "AI coding startup raises new venture funding",
            "markdown_context": "An AI coding startup raised a new financing round as investor interest in developer tooling continued."
        }
    ]
}
""".strip(),
        assistant_response="""
{
    "topics": [
        {
            "primary_signal_id": "11",
            "supporting_signal_ids": [
                "12"
            ],
            "editorial_goal": "Establish that autonomous software engineering is becoming a broader product direction rather than an isolated feature, using the two coding platforms together to show the shift from assisting with code toward delegating larger implementation workflows.",
            "duration_weight": 3
        },
        {
            "primary_signal_id": "13",
            "supporting_signal_ids": [
                "11",
                "12"
            ],
            "editorial_goal": "Explain why increasingly autonomous coding agents require evaluation against realistic engineering workflows, connecting the benchmark to the expanding scope of responsibility these systems are being given.",
            "duration_weight": 2
        }
    ]
}
""".strip(),
        user_feedback=(
            "Combines the two product announcements into one topic because "
            "they establish the same broader shift toward autonomous software "
            "engineering. The benchmark becomes a separate topic because it "
            "advances a distinct consequence of that shift: the need for more "
            "realistic evaluation. The funding signal is omitted because it "
            "does not materially advance the segment's narrative goal, and "
            "the relative weights give greater emphasis to establishing the "
            "underlying product transition before discussing its evaluation "
            "implications."
        ),
    ),
]
