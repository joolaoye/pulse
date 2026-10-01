from pulse.services.retrieval import XRetriever
from pulse.types import AugmentedXSignal, ScoredSignal, Tweet

DEFAULT_TOP_COMMENTS = 10


class XSignalAugmenter:
    def __init__(
        self,
        *,
        x_retriever: XRetriever,
        top_comments: int = DEFAULT_TOP_COMMENTS,
    ) -> None:
        self.x_retriever = x_retriever
        self.top_comments = top_comments

    async def augment(
        self,
        *,
        scored_signal: ScoredSignal,
    ) -> AugmentedXSignal:
        discourse = await self.x_retriever.retrieve_conversation(
            conversation_id=scored_signal.signal_id,
        )

        replies = [
            tweet
            for tweet in discourse.tweets
            if self._is_community_reply(
                tweet=tweet,
                root_tweet=discourse.root_tweet,
            )
        ]

        replies.sort(
            key=self._reply_score,
            reverse=True,
        )

        return AugmentedXSignal(
            signal_id=scored_signal.signal_id,
            author_username=discourse.root_author_username,
            top_comments=[tweet.text for tweet in replies[: self.top_comments] if tweet.text],
        )

    @staticmethod
    def _is_community_reply(
        *,
        tweet: Tweet,
        root_tweet: Tweet,
    ) -> bool:
        return (
            tweet.id != root_tweet.id
            and tweet.author_id != root_tweet.author_id
            and tweet.in_reply_to_user_id == root_tweet.author_id
        )

    @staticmethod
    def _reply_score(
        tweet: Tweet,
    ) -> int:
        if not tweet.public_metrics:
            return 0

        return tweet.public_metrics.like_count + tweet.public_metrics.retweet_count
