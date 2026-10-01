import pytest

from pulse.services.signals.canonicalizer import XGenerationCanonicalizer
from pulse.types import AugmentedXSignal, ProcessedSignal, ScoredSignal, Signal


def _canonicalize(
    comments: list[str],
    *,
    content: str = "Launch day https://t.co/abc\n\nMore detail",
) -> ProcessedSignal:
    return XGenerationCanonicalizer.canonicalize(
        signal=Signal(
            id="100",
            source="x",
            content=content,
        ),
        scored_signal=ScoredSignal(
            signal_id="100",
            relevance_score=0.91,
            interest_matches=[],
        ),
        augmented_signal=AugmentedXSignal(
            signal_id="100",
            author_username="Ada",
            top_comments=comments,
        ),
    )


def test_processed_signal_keeps_identity_score_and_cleaned_comments() -> None:
    processed = _canonicalize(
        [
            "@Ada Nice post",
            "",
            "Line one\n\nLine two",
        ]
    )

    assert processed.signal_id == "100"
    assert processed.source == "x"
    assert processed.relevance_score == 0.91
    assert processed.title == "Launch day"
    assert "https://t.co/abc" not in processed.markdown_context
    assert "More detail" in processed.markdown_context
    assert "- Nice post" in processed.markdown_context
    assert "- Line one Line two" in processed.markdown_context
    assert "@Ada" not in processed.markdown_context


@pytest.mark.parametrize(
    "first_line_length",
    [120, 121],
)
def test_title_is_cut_at_120_characters(first_line_length: int) -> None:
    first_line = "A" * first_line_length
    processed = _canonicalize(
        [],
        content=f"{first_line}\n\nRest of the post",
    )

    assert processed.title == first_line[:120]
    assert len(processed.title) == 120
    assert first_line in processed.markdown_context
    assert "Rest of the post" in processed.markdown_context


def test_processed_signal_omits_reactions_when_there_are_no_comments() -> None:
    processed = _canonicalize([])

    assert processed.signal_id == "100"
    assert processed.relevance_score == 0.91
    assert "Community Reactions" not in processed.markdown_context
