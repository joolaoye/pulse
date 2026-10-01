from typing import Any, cast

import pytest

from pulse.services.signals.signal_augmenter import XSignalAugmenter
from pulse.types import Discourse, DiscourseType, PublicMetrics, ScoredSignal, Tweet


def _tweet(
    tweet_id: str,
    text: str,
    *,
    author_id: str,
    in_reply_to_user_id: str | None = None,
    likes: int | None = None,
    reposts: int = 0,
) -> Tweet:
    metrics = None
    if likes is not None:
        metrics = PublicMetrics(
            like_count=likes,
            retweet_count=reposts,
        )

    return Tweet(
        id=tweet_id,
        text=text,
        author_id=author_id,
        in_reply_to_user_id=in_reply_to_user_id,
        public_metrics=metrics,
    )


ROOT = _tweet(
    "100",
    "Root post",
    author_id="author",
)


class FakeRetriever:
    def __init__(
        self,
        tweets: list[Tweet],
    ) -> None:
        self.tweets = tweets
        self.conversation_ids: list[str] = []

    async def retrieve_conversation(
        self,
        *,
        conversation_id: str,
    ) -> Discourse:
        self.conversation_ids.append(conversation_id)
        return Discourse(
            discourse_type=DiscourseType.THREAD,
            root_tweet=ROOT,
            tweets=self.tweets,
            root_author_username="ada",
        )


def _augmenter(
    tweets: list[Tweet],
    *,
    top_comments: int = 10,
) -> tuple[XSignalAugmenter, FakeRetriever]:
    retriever = FakeRetriever(tweets)
    augmenter = XSignalAugmenter(
        x_retriever=cast(Any, retriever),
        top_comments=top_comments,
    )
    return augmenter, retriever


def _scored() -> ScoredSignal:
    return ScoredSignal(
        signal_id="100",
        relevance_score=0.8,
        interest_matches=[],
    )


async def test_augmentation_keeps_signal_identity_and_highest_scoring_replies() -> None:
    augmenter, retriever = _augmenter(
        [
            ROOT,
            _tweet(
                "low",
                "Low",
                author_id="reader-1",
                in_reply_to_user_id="author",
                likes=1,
            ),
            _tweet(
                "high",
                "High",
                author_id="reader-2",
                in_reply_to_user_id="author",
                likes=2,
                reposts=10,
            ),
            _tweet(
                "unscored",
                "Unscored",
                author_id="reader-3",
                in_reply_to_user_id="author",
            ),
        ],
        top_comments=2,
    )

    augmented = await augmenter.augment(scored_signal=_scored())

    assert retriever.conversation_ids == ["100"]
    assert augmented.signal_id == "100"
    assert augmented.author_username == "ada"
    assert augmented.top_comments == ["High", "Low"]


@pytest.mark.parametrize(
    "reply",
    [
        ROOT,
        _tweet(
            "self",
            "Self reply",
            author_id="author",
            in_reply_to_user_id="author",
            likes=50,
        ),
        _tweet(
            "aside",
            "Reply to someone else",
            author_id="reader",
            in_reply_to_user_id="other-user",
            likes=50,
        ),
        _tweet(
            "blank",
            "",
            author_id="reader",
            in_reply_to_user_id="author",
            likes=50,
        ),
    ],
)
async def test_non_community_replies_are_not_attached(
    reply: Tweet,
) -> None:
    community = _tweet(
        "community",
        "Community reply",
        author_id="reader",
        in_reply_to_user_id="author",
        likes=1,
    )
    augmenter, _retriever = _augmenter([ROOT, reply, community])

    augmented = await augmenter.augment(scored_signal=_scored())

    assert augmented.signal_id == "100"
    assert augmented.top_comments == ["Community reply"]
