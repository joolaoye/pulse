from typing import Dict, List

from pydantic import BaseModel

from pulse.types import (
    Tweet,
    XUser,
)


class XRetrievalContext(BaseModel):
    tweets_by_id: Dict[str, Tweet]
    users_by_id: Dict[str, XUser]
    primary_tweet_ids: List[str]
