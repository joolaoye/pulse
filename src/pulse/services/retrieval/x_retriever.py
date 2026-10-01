from datetime import datetime, timedelta, timezone
import re
from typing import Dict, List, Set

from pulse.infrastructure.db.repositories import XDiscourseCacheRepository
from pulse.infrastructure.x import (
    Includes,
    TimelineResponse,
    XClient,
    XRetrievalContext,
)
from pulse.services.retrieval.discourse_reconstructor import DiscourseReconstructor
from pulse.types import (
    CachedXDiscourse,
    Discourse,
    Tweet,
    XUser,
)

URL_PATTERN = re.compile(r"https?://\S+")
CACHE_FRESHNESS = timedelta(hours=24)


class XRetriever:
    def __init__(
        self,
        *,
        client: XClient,
        cache_repository: XDiscourseCacheRepository,
        discourse_reconstructor: DiscourseReconstructor,
    ) -> None:
        self.client = client
        self.cache_repository = cache_repository
        self.discourse_reconstructor = discourse_reconstructor

    async def retrieve(
        self,
        *,
        list_id: str,
    ) -> List[Discourse]:
        timeline = await self._load_timeline(list_id=list_id)
        conversation_ids = self._get_conversation_ids(context=timeline)

        discourses: List[Discourse] = []

        for conversation_id in conversation_ids:
            discourse = await self.retrieve_conversation(
                conversation_id=conversation_id,
            )

            if self._has_usable_text(discourse=discourse):
                discourses.append(discourse)

        return discourses

    async def retrieve_conversation(
        self,
        *,
        conversation_id: str,
    ) -> Discourse:
        cached = await self.cache_repository.get(
            conversation_id=conversation_id,
        )

        if cached is None:
            return await self._hydrate_conversation(
                conversation_id=conversation_id,
            )

        if self._is_fresh(cached=cached):
            return cached.discourse

        return await self._refresh_conversation(
            cached=cached,
        )

    async def _hydrate_conversation(
        self,
        *,
        conversation_id: str,
    ) -> Discourse:
        root_payload = await self.client.fetch_tweet_by_id(
            tweet_id=conversation_id,
        )

        conversation_payload = await self.client.fetch_conversation_tweets(
            conversation_id=conversation_id, since_id=None
        )

        root = TimelineResponse.model_validate(self._normalize_single_tweet_payload(root_payload))

        conversation = TimelineResponse.model_validate(conversation_payload)

        context = self._build_context(
            self._merge_payloads(
                [
                    root,
                    conversation,
                ]
            )
        )

        discourse = self.discourse_reconstructor.reconstruct(
            context=context,
            root_tweet_id=conversation_id,
        )

        await self._persist_discourse(
            conversation_id=conversation_id,
            discourse=discourse,
        )

        return discourse

    async def _refresh_conversation(
        self,
        *,
        cached: CachedXDiscourse,
    ) -> Discourse:
        payload = await self.client.fetch_conversation_tweets(
            conversation_id=cached.conversation_id,
            since_id=cached.latest_post_id,
        )

        parsed = TimelineResponse.model_validate(payload)

        context = self._build_context(
            parsed,
            existing_tweets=cached.discourse.tweets,
        )

        discourse = self.discourse_reconstructor.reconstruct(
            context=context,
            root_tweet_id=cached.conversation_id,
        )

        if (
            discourse.root_author_username is None
            and cached.discourse.root_author_username is not None
        ):
            discourse = discourse.model_copy(
                update={"root_author_username": (cached.discourse.root_author_username)}
            )

        await self._persist_discourse(
            conversation_id=cached.conversation_id,
            discourse=discourse,
        )

        return discourse

    @staticmethod
    def _build_context(
        payload: TimelineResponse,
        *,
        existing_tweets: List[Tweet] | None = None,
    ) -> XRetrievalContext:
        tweets_by_id: Dict[str, Tweet] = {tweet.id: tweet for tweet in existing_tweets or []}

        users_by_id: Dict[str, XUser] = {}

        for tweet in payload.data:
            tweets_by_id[tweet.id] = tweet

        for tweet in payload.includes.tweets:
            tweets_by_id[tweet.id] = tweet

        for user in payload.includes.users:
            users_by_id[user.id] = user

        return XRetrievalContext(
            tweets_by_id=tweets_by_id,
            users_by_id=users_by_id,
            primary_tweet_ids=[tweet.id for tweet in payload.data],
        )

    async def _load_timeline(
        self,
        *,
        list_id: str,
    ) -> XRetrievalContext:
        payload = await self.client.fetch_list_timeline(
            list_id=list_id,
        )

        return self._build_context(TimelineResponse.model_validate(payload))

    async def _persist_discourse(
        self,
        *,
        conversation_id: str,
        discourse: Discourse,
    ) -> None:
        await self.cache_repository.persist(
            cached_discourse=CachedXDiscourse(
                conversation_id=conversation_id,
                discourse=discourse,
                latest_post_id=self._get_latest_post_id(
                    conversation_id=conversation_id,
                    discourse=discourse,
                ),
                refreshed_at=datetime.now(timezone.utc),
            )
        )

    @staticmethod
    def _is_fresh(
        *,
        cached: CachedXDiscourse,
    ) -> bool:
        return datetime.now(timezone.utc) - cached.refreshed_at < CACHE_FRESHNESS

    @staticmethod
    def _get_latest_post_id(
        *,
        conversation_id: str,
        discourse: Discourse,
    ) -> str:
        conversation_tweets = [
            tweet
            for tweet in discourse.tweets
            if (tweet.conversation_id == conversation_id or tweet.id == conversation_id)
        ]

        if not conversation_tweets:
            raise ValueError(f"No tweets found for conversation {conversation_id}.")

        return max(
            (tweet.id for tweet in conversation_tweets),
            key=int,
        )

    @staticmethod
    def _has_usable_text(
        *,
        discourse: Discourse,
    ) -> bool:
        return any(URL_PATTERN.sub("", tweet.text).strip() for tweet in discourse.tweets)

    @staticmethod
    def _get_conversation_ids(
        *,
        context: XRetrievalContext,
    ) -> List[str]:
        conversation_ids: List[str] = []
        seen: Set[str] = set()

        for tweet_id in context.primary_tweet_ids:
            tweet = context.tweets_by_id[tweet_id]
            conversation_id = tweet.conversation_id or tweet.id

            if conversation_id in seen:
                continue

            seen.add(conversation_id)
            conversation_ids.append(conversation_id)

        return conversation_ids

    @staticmethod
    def _normalize_single_tweet_payload(
        payload: dict,
    ) -> dict:
        data = payload.get("data")

        return {
            "data": [data] if data else [],
            "includes": payload.get("includes", {}),
            "meta": {},
        }

    @staticmethod
    def _merge_payloads(
        payloads: List[TimelineResponse],
    ) -> TimelineResponse:
        tweets: Dict[str, Tweet] = {}
        users: Dict[str, XUser] = {}

        for payload in payloads:
            for tweet in payload.data:
                tweets[tweet.id] = tweet

            for tweet in payload.includes.tweets:
                tweets[tweet.id] = tweet

            for user in payload.includes.users:
                users[user.id] = user

        return TimelineResponse(
            data=list(tweets.values()),
            includes=Includes(
                users=list(users.values()),
                tweets=list(tweets.values()),
            ),
            meta={},
        )
