from datetime import datetime, timezone

from pulse.infrastructure.x.context import XRetrievalContext
from pulse.services.retrieval.discourse_reconstructor import DiscourseReconstructor
from pulse.types import Tweet, XUser


def _tweet(
    tweet_id: str,
    created_at: datetime | None,
) -> Tweet:
    return Tweet(
        id=tweet_id,
        text=tweet_id,
        author_id="user-1",
        created_at=created_at,
        conversation_id="post-a",
        in_reply_to_user_id=None if tweet_id == "post-a" else "user-1",
    )


def test_thread_continuations_are_ordered_by_time_with_undated_posts_last() -> None:
    earliest = _tweet("post-a", datetime(2026, 10, 1, 9, tzinfo=timezone.utc))
    later = _tweet("post-b", datetime(2026, 10, 1, 10, tzinfo=timezone.utc))
    undated = _tweet("post-c", None)
    context = XRetrievalContext(
        tweets_by_id={
            "post-c": undated,
            "post-b": later,
            "post-a": earliest,
        },
        users_by_id={"user-1": XUser(id="user-1", username="ada")},
        primary_tweet_ids=["post-a"],
    )

    discourse = DiscourseReconstructor.reconstruct(context, "post-a")

    assert [tweet.id for tweet in discourse.tweets] == ["post-a", "post-b", "post-c"]
