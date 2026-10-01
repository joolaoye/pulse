from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DiscourseType(str, Enum):
    STANDALONE = "standalone"
    THREAD = "thread"
    QUOTE = "quote"


class XUser(BaseModel):
    id: str
    username: str
    name: Optional[str] = None


class ReferencedTweet(BaseModel):
    id: str
    type: str


class PublicMetrics(BaseModel):
    like_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    retweet_count: int = 0


class Tweet(BaseModel):
    id: str
    text: str
    author_id: Optional[str] = None
    created_at: Optional[datetime] = None
    conversation_id: Optional[str] = None
    in_reply_to_user_id: Optional[str] = None
    referenced_tweets: List[ReferencedTweet] = Field(default_factory=list)
    public_metrics: Optional[PublicMetrics] = None


class Discourse(BaseModel):
    discourse_type: DiscourseType
    root_tweet: Tweet
    tweets: List[Tweet] = Field(default_factory=list)
    referenced_tweet: Optional[Tweet] = None
    root_author_username: Optional[str] = None


class CachedXDiscourse(BaseModel):
    conversation_id: str
    discourse: Discourse
    latest_post_id: str
    refreshed_at: datetime
