import re
from typing import List

from pulse.types import (
    AugmentedXSignal,
    ProcessedSignal,
    ScoredSignal,
    Signal,
)


class XGenerationCanonicalizer:
    @staticmethod
    def canonicalize(
        *,
        signal: Signal,
        scored_signal: ScoredSignal,
        augmented_signal: AugmentedXSignal,
    ) -> ProcessedSignal:
        return ProcessedSignal(
            signal_id=signal.id,
            title=XGenerationCanonicalizer._extract_title(signal.content),
            markdown_context=(
                XGenerationCanonicalizer._build_markdown_context(
                    content=signal.content,
                    augmented_signal=augmented_signal,
                )
            ),
            relevance_score=scored_signal.relevance_score,
            source=signal.source,
        )

    @staticmethod
    def _build_markdown_context(
        *,
        content: str,
        augmented_signal: AugmentedXSignal,
    ) -> str:
        cleaned_content = XGenerationCanonicalizer._clean_text(content)

        cleaned_comments = XGenerationCanonicalizer._clean_comments(
            comments=augmented_signal.top_comments,
            author_username=augmented_signal.author_username,
        )

        sections = [
            "# Original Post",
            "",
            cleaned_content,
        ]

        if cleaned_comments:
            sections.extend(
                [
                    "",
                    "## Community Reactions",
                    "",
                    *[f"- {comment}" for comment in cleaned_comments],
                ]
            )

        return "\n".join(sections)

    @staticmethod
    def _extract_title(text: str) -> str:
        cleaned = XGenerationCanonicalizer._clean_text(text)
        return cleaned.splitlines()[0].strip()[:120]

    @staticmethod
    def _clean_comments(
        *,
        comments: List[str],
        author_username: str | None,
    ) -> List[str]:
        cleaned_comments: List[str] = []

        for comment in comments:
            cleaned = XGenerationCanonicalizer._clean_text(comment)
            cleaned = re.sub(
                r"\s*\n+\s*",
                " ",
                cleaned,
            )

            if author_username:
                cleaned = re.sub(
                    rf"^@{re.escape(author_username)}\s*",
                    "",
                    cleaned,
                    flags=re.IGNORECASE,
                )

            if cleaned:
                cleaned_comments.append(cleaned)

        return cleaned_comments

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(
            r"https://t\.co/\S+",
            "",
            text.strip(),
        )
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()
