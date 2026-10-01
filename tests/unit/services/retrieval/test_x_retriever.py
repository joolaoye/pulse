from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import pytest

from pulse.services.retrieval.discourse_reconstructor import (
    DiscourseReconstructor,
)
from pulse.services.retrieval.x_retriever import XRetriever
from pulse.types import CachedXDiscourse, Discourse, DiscourseType, Tweet

ROOT_ID = "100"
REPLY_ID = "110"
NEW_REPLY_ID = "120"
AUTHOR_ID = "author-1"


def tweet_payload(
    tweet_id: str,
    *,
    text: str,
    conversation_id: str = ROOT_ID,
    reply: bool = False,
) -> dict:
    return {
        "id": tweet_id,
        "text": text,
        "author_id": AUTHOR_ID,
        "conversation_id": conversation_id,
        "in_reply_to_user_id": AUTHOR_ID if reply else None,
        "created_at": "2026-09-12T12:00:00Z",
    }


def timeline_payload(*tweets: dict) -> dict:
    return {
        "data": list(tweets),
        "includes": {
            "users": [],
            "tweets": [],
        },
        "meta": {},
    }


def root_payload(tweet: dict) -> dict:
    return {
        "data": tweet,
        "includes": {
            "users": [],
            "tweets": [],
        },
    }


class FakeXClient:
    def __init__(
        self,
        *,
        timeline: dict,
        root: dict,
        conversation: dict,
        incremental: Optional[dict] = None,
    ) -> None:
        self.timeline = timeline
        self.root = root
        self.conversation = conversation
        self.incremental = incremental or timeline_payload()

        self.root_calls = 0
        self.conversation_calls = 0
        self.since_ids = []

    async def fetch_list_timeline(
        self,
        *,
        list_id: str,
    ) -> dict:
        return self.timeline

    async def fetch_tweet_by_id(
        self,
        *,
        tweet_id: str,
    ) -> dict:
        self.root_calls += 1
        return self.root

    async def fetch_conversation_tweets(
        self,
        *,
        conversation_id: str,
        since_id: Optional[str] = None,
    ) -> dict:
        self.conversation_calls += 1
        self.since_ids.append(since_id)

        if since_id:
            return self.incremental

        return self.conversation


class FakeCacheRepository:
    def __init__(self) -> None:
        self.records: Dict[str, CachedXDiscourse] = {}
        self.persist_count = 0

    async def get(
        self,
        *,
        conversation_id: str,
    ) -> Optional[CachedXDiscourse]:
        return self.records.get(conversation_id)

    async def persist(
        self,
        *,
        cached_discourse: CachedXDiscourse,
    ) -> None:
        self.persist_count += 1
        self.records[cached_discourse.conversation_id] = cached_discourse


def build_retriever(
    *,
    client: FakeXClient,
    cache: FakeCacheRepository,
) -> XRetriever:
    return XRetriever(
        client=client,  # type: ignore[arg-type]
        cache_repository=cache,  # type: ignore[arg-type]
        discourse_reconstructor=DiscourseReconstructor(),
    )


@pytest.mark.asyncio
async def test_cache_miss_hydrates_and_persists() -> None:
    root = tweet_payload(
        ROOT_ID,
        text="Root post",
    )

    reply = tweet_payload(
        REPLY_ID,
        text="Thread continuation",
        reply=True,
    )

    client = FakeXClient(
        timeline=timeline_payload(root),
        root=root_payload(root),
        conversation=timeline_payload(reply),
    )

    cache = FakeCacheRepository()

    retriever = build_retriever(
        client=client,
        cache=cache,
    )

    discourses = await retriever.retrieve(list_id="list-1")

    assert len(discourses) == 1
    assert discourses[0].discourse_type == DiscourseType.THREAD

    assert {tweet.id for tweet in discourses[0].tweets} == {
        ROOT_ID,
        REPLY_ID,
    }

    assert client.root_calls == 1
    assert client.conversation_calls == 1
    assert client.since_ids == [None]

    assert cache.persist_count == 1
    assert cache.records[ROOT_ID].latest_post_id == REPLY_ID


@pytest.mark.asyncio
async def test_fresh_cache_skips_conversation_hydration() -> None:
    root = Tweet.model_validate(
        tweet_payload(
            ROOT_ID,
            text="Cached root",
        )
    )

    discourse = Discourse(
        discourse_type=DiscourseType.STANDALONE,
        root_tweet=root,
        tweets=[root],
    )

    cache = FakeCacheRepository()
    cache.records[ROOT_ID] = CachedXDiscourse(
        conversation_id=ROOT_ID,
        discourse=discourse,
        latest_post_id=ROOT_ID,
        refreshed_at=datetime.now(timezone.utc),
    )

    client = FakeXClient(
        timeline=timeline_payload(
            tweet_payload(
                ROOT_ID,
                text="Timeline root",
            )
        ),
        root={},
        conversation={},
    )

    retriever = build_retriever(
        client=client,
        cache=cache,
    )

    discourses = await retriever.retrieve(list_id="list-1")

    assert len(discourses) == 1
    assert discourses[0].root_tweet.id == ROOT_ID

    assert client.root_calls == 0
    assert client.conversation_calls == 0
    assert cache.persist_count == 0


@pytest.mark.asyncio
async def test_stale_cache_incrementally_refreshes() -> None:
    root = Tweet.model_validate(
        tweet_payload(
            ROOT_ID,
            text="Root post",
        )
    )

    reply = Tweet.model_validate(
        tweet_payload(
            REPLY_ID,
            text="Existing reply",
            reply=True,
        )
    )

    cached_discourse = Discourse(
        discourse_type=DiscourseType.THREAD,
        root_tweet=root,
        tweets=[
            root,
            reply,
        ],
    )

    cache = FakeCacheRepository()
    cache.records[ROOT_ID] = CachedXDiscourse(
        conversation_id=ROOT_ID,
        discourse=cached_discourse,
        latest_post_id=REPLY_ID,
        refreshed_at=(datetime.now(timezone.utc) - timedelta(hours=25)),
    )

    client = FakeXClient(
        timeline=timeline_payload(
            tweet_payload(
                ROOT_ID,
                text="Timeline root",
            )
        ),
        root={},
        conversation={},
        incremental=timeline_payload(
            tweet_payload(
                NEW_REPLY_ID,
                text="New reply",
                reply=True,
            )
        ),
    )

    retriever = build_retriever(
        client=client,
        cache=cache,
    )

    discourses = await retriever.retrieve(list_id="list-1")

    assert client.root_calls == 0
    assert client.conversation_calls == 1
    assert client.since_ids == [REPLY_ID]

    assert {tweet.id for tweet in discourses[0].tweets} == {
        ROOT_ID,
        REPLY_ID,
        NEW_REPLY_ID,
    }

    updated = cache.records[ROOT_ID]

    assert updated.latest_post_id == NEW_REPLY_ID
    assert cache.persist_count == 1


@pytest.mark.asyncio
async def test_timeline_deduplicates_conversations() -> None:
    first = tweet_payload(
        ROOT_ID,
        text="Root",
    )

    second = tweet_payload(
        "105",
        text="Another timeline post",
        conversation_id=ROOT_ID,
        reply=True,
    )

    client = FakeXClient(
        timeline=timeline_payload(
            first,
            second,
        ),
        root=root_payload(first),
        conversation=timeline_payload(),
    )

    cache = FakeCacheRepository()

    retriever = build_retriever(
        client=client,
        cache=cache,
    )

    await retriever.retrieve(list_id="list-1")

    assert client.root_calls == 1
    assert client.conversation_calls == 1


@pytest.mark.asyncio
async def test_stale_cache_refreshes_when_no_new_posts() -> None:
    root = Tweet.model_validate(tweet_payload(ROOT_ID, text="Root"))

    cached = Discourse(
        discourse_type=DiscourseType.STANDALONE,
        root_tweet=root,
        tweets=[root],
    )

    cache = FakeCacheRepository()
    old_refreshed_at = datetime.now(timezone.utc) - timedelta(hours=25)

    cache.records[ROOT_ID] = CachedXDiscourse(
        conversation_id=ROOT_ID,
        discourse=cached,
        latest_post_id=ROOT_ID,
        refreshed_at=old_refreshed_at,
    )

    client = FakeXClient(
        timeline=timeline_payload(tweet_payload(ROOT_ID, text="Root")),
        root={},
        conversation={},
        incremental=timeline_payload(),
    )

    retriever = build_retriever(
        client=client,
        cache=cache,
    )

    await retriever.retrieve(list_id="list-1")

    updated = cache.records[ROOT_ID]

    assert client.since_ids == [ROOT_ID]
    assert updated.latest_post_id == ROOT_ID
    assert updated.refreshed_at > old_refreshed_at
    assert cache.persist_count == 1


def test_latest_post_id_ignores_other_conversations() -> None:
    root = Tweet.model_validate(tweet_payload(ROOT_ID, text="Quote"))

    unrelated = Tweet.model_validate(
        tweet_payload(
            "999",
            text="Quoted post",
            conversation_id="999",
        )
    )

    discourse = Discourse(
        discourse_type=DiscourseType.QUOTE,
        root_tweet=root,
        referenced_tweet=unrelated,
        tweets=[
            root,
            unrelated,
        ],
    )

    latest_post_id = XRetriever._get_latest_post_id(
        conversation_id=ROOT_ID,
        discourse=discourse,
    )

    assert latest_post_id == ROOT_ID
