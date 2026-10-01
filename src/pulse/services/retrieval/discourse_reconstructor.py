from typing import List, Optional

from pulse.infrastructure.x import XRetrievalContext
from pulse.types import (
    Discourse,
    DiscourseType,
    Tweet,
)


class DiscourseReconstructor:
    @staticmethod
    def reconstruct(
        context: XRetrievalContext,
        root_tweet_id: str,
    ) -> Discourse:
        root_tweet = context.tweets_by_id.get(root_tweet_id)

        if not root_tweet:
            raise ValueError(f"Root tweet {root_tweet_id} not found in context.")

        if not root_tweet.author_id:
            raise ValueError(f"Root tweet {root_tweet_id} does not have an author_id.")

        root_author_username = DiscourseReconstructor._resolve_root_author_username(
            context=context,
            root_tweet=root_tweet,
        )

        discourse_type = DiscourseReconstructor.detect_discourse_type(
            context=context,
            root_tweet=root_tweet,
        )

        if discourse_type == DiscourseType.THREAD:
            return DiscourseReconstructor.reconstruct_thread(
                context=context,
                root_tweet=root_tweet,
                root_author_username=root_author_username,
            )

        if discourse_type == DiscourseType.QUOTE:
            return DiscourseReconstructor.reconstruct_quote(
                context=context,
                root_tweet=root_tweet,
                root_author_username=root_author_username,
            )

        return DiscourseReconstructor.reconstruct_standalone(
            root_tweet=root_tweet,
            root_author_username=root_author_username,
        )

    @staticmethod
    def reconstruct_thread(
        context: XRetrievalContext,
        root_tweet: Tweet,
        root_author_username: Optional[str],
    ) -> Discourse:
        root_author_id = root_tweet.author_id

        if not root_author_id:
            raise ValueError("Root tweet author_id missing.")

        canonical_thread = [
            tweet
            for tweet in context.tweets_by_id.values()
            if DiscourseReconstructor.is_thread_continuation(
                tweet=tweet,
                root_tweet_id=root_tweet.id,
                root_author_id=root_author_id,
            )
        ]

        canonical_thread.sort(
            key=lambda tweet: (
                tweet.created_at.timestamp() if tweet.created_at is not None else float("inf")
            )
        )

        return Discourse(
            discourse_type=DiscourseType.THREAD,
            root_tweet=root_tweet,
            tweets=canonical_thread,
            root_author_username=root_author_username,
        )

    @staticmethod
    def reconstruct_quote(
        context: XRetrievalContext,
        root_tweet: Tweet,
        root_author_username: Optional[str],
    ) -> Discourse:
        referenced_tweet = None

        if root_tweet.referenced_tweets:
            referenced = root_tweet.referenced_tweets[0]
            referenced_tweet = context.tweets_by_id.get(referenced.id)

        tweets: List[Tweet] = [root_tweet]

        if referenced_tweet:
            tweets.append(referenced_tweet)

        return Discourse(
            discourse_type=DiscourseType.QUOTE,
            root_tweet=root_tweet,
            referenced_tweet=referenced_tweet,
            tweets=tweets,
            root_author_username=root_author_username,
        )

    @staticmethod
    def reconstruct_standalone(
        root_tweet: Tweet,
        root_author_username: Optional[str],
    ) -> Discourse:
        return Discourse(
            discourse_type=DiscourseType.STANDALONE,
            root_tweet=root_tweet,
            tweets=[root_tweet],
            root_author_username=root_author_username,
        )

    @staticmethod
    def _resolve_root_author_username(
        *,
        context: XRetrievalContext,
        root_tweet: Tweet,
    ) -> Optional[str]:
        if not root_tweet.author_id:
            return None

        author = context.users_by_id.get(root_tweet.author_id)

        return author.username if author else None

    @staticmethod
    def is_thread_continuation(
        tweet: Tweet,
        root_tweet_id: str,
        root_author_id: str,
    ) -> bool:
        if tweet.id == root_tweet_id:
            return True

        return tweet.author_id == root_author_id and tweet.in_reply_to_user_id == root_author_id

    @staticmethod
    def detect_discourse_type(
        context: XRetrievalContext,
        root_tweet: Tweet,
    ) -> DiscourseType:
        if root_tweet.referenced_tweets:
            referenced_tweet = root_tweet.referenced_tweets[0]

            if referenced_tweet.type == "quoted":
                return DiscourseType.QUOTE

        has_self_thread_continuation = any(
            tweet.author_id == root_tweet.author_id
            and tweet.in_reply_to_user_id == root_tweet.author_id
            and tweet.id != root_tweet.id
            for tweet in context.tweets_by_id.values()
        )

        if has_self_thread_continuation:
            return DiscourseType.THREAD

        return DiscourseType.STANDALONE
