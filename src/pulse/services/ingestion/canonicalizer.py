import re
from typing import List

from pulse.types import (
    Discourse,
    DiscourseType,
    Signal,
)


class XCanonicalizer:
    @staticmethod
    def canonicalize(
        discourse: Discourse,
    ) -> Signal:
        if discourse.discourse_type == DiscourseType.THREAD:
            return XCanonicalizer.canonicalize_thread(
                discourse=discourse,
            )

        if discourse.discourse_type == DiscourseType.QUOTE:
            return XCanonicalizer.canonicalize_quote(
                discourse=discourse,
            )

        return XCanonicalizer.canonicalize_standalone(
            discourse=discourse,
        )

    @staticmethod
    def canonicalize_thread(
        discourse: Discourse,
    ) -> Signal:
        thread_content: List[str] = []

        for tweet in discourse.tweets:
            cleaned_text = XCanonicalizer.clean_text(tweet.text)

            if cleaned_text:
                thread_content.append(cleaned_text)

        content = "\n\n".join(thread_content)

        return Signal(
            id=(discourse.root_tweet.id),
            source="x",
            content=content,
        )

    @staticmethod
    def canonicalize_quote(
        discourse: Discourse,
    ) -> Signal:
        content_parts: List[str] = []

        quote_commentary = XCanonicalizer.clean_text(discourse.root_tweet.text)

        if quote_commentary:
            content_parts.append(quote_commentary)

        if discourse.referenced_tweet:
            referenced_content = XCanonicalizer.clean_text(discourse.referenced_tweet.text)

            if referenced_content:
                content_parts.append(referenced_content)

        content = "\n\n".join(content_parts)

        return Signal(
            id=(discourse.root_tweet.id),
            source="x",
            content=content,
        )

    @staticmethod
    def canonicalize_standalone(
        discourse: Discourse,
    ) -> Signal:
        return Signal(
            id=(discourse.root_tweet.id),
            source="x",
            content=(XCanonicalizer.clean_text(discourse.root_tweet.text)),
        )

    @staticmethod
    def clean_text(
        text: str,
    ) -> str:
        cleaned_text = text.strip()

        cleaned_text = re.sub(
            r"https://t\.co/\S+",
            "",
            cleaned_text,
        )

        cleaned_text = re.sub(
            r"\n{3,}",
            "\n\n",
            cleaned_text,
        )

        cleaned_text = re.sub(
            r"[ \t]{2,}",
            " ",
            cleaned_text,
        )

        return cleaned_text.strip()
