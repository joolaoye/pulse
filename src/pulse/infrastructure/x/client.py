from typing import Dict, Optional, Union

import httpx

from pulse.infrastructure.x.config import ClientConfig

LIST_TIMELINE_ENDPOINT = "/lists/{list_id}/tweets"
SEARCH_RECENT_TWEETS_ENDPOINT = "/tweets/search/recent"
TWEET_BY_ID_ENDPOINT = "/tweets/{tweet_id}"
DEFAULT_TWEET_FIELDS = [
    "created_at",
    "author_id",
    "conversation_id",
    "public_metrics",
    "referenced_tweets",
    "in_reply_to_user_id",
]
DEFAULT_USER_FIELDS = [
    "username",
    "name",
]
DEFAULT_EXPANSIONS = [
    "author_id",
    "referenced_tweets.id",
    "referenced_tweets.id.author_id",
]


class XClient:
    def __init__(
        self,
        *,
        bearer_token: str,
        config: ClientConfig,
    ) -> None:
        self.config = config
        self.http_client = httpx.AsyncClient(
            base_url=config.api_base_url,
            headers={
                "Authorization": f"Bearer {bearer_token}",
            },
            timeout=config.request_timeout_seconds,
        )

    async def fetch_tweet_by_id(
        self,
        *,
        tweet_id: str,
    ) -> dict:
        response = await self.http_client.get(
            TWEET_BY_ID_ENDPOINT.format(tweet_id=tweet_id),
            params=self._default_params(),
        )

        response.raise_for_status()
        return response.json()

    async def fetch_list_timeline(
        self,
        *,
        list_id: str,
    ) -> dict:
        params = self._default_params()
        params["max_results"] = self.config.list_timeline_max_results

        response = await self.http_client.get(
            LIST_TIMELINE_ENDPOINT.format(list_id=list_id),
            params=params,
        )

        response.raise_for_status()
        return response.json()

    async def fetch_conversation_tweets(
        self,
        *,
        conversation_id: str,
        since_id: Optional[str] = None,
    ) -> dict:
        params = self._default_params()
        params.update(
            {
                "query": f"conversation_id:{conversation_id}",
                "max_results": self.config.conversation_max_results,
            }
        )

        if since_id:
            params["since_id"] = since_id

        response = await self.http_client.get(
            SEARCH_RECENT_TWEETS_ENDPOINT,
            params=params,
        )

        response.raise_for_status()
        return response.json()

    async def aclose(self) -> None:
        await self.http_client.aclose()

    @staticmethod
    def _default_params() -> Dict[str, Union[str, int]]:
        return {
            "tweet.fields": ",".join(DEFAULT_TWEET_FIELDS),
            "user.fields": ",".join(DEFAULT_USER_FIELDS),
            "expansions": ",".join(DEFAULT_EXPANSIONS),
        }
