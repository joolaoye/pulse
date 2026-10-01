from typing import Any, Dict, List

from pydantic import BaseModel, Field

from pulse.types import Tweet, XUser


class Includes(BaseModel):
    users: List[XUser] = Field(default_factory=list)
    tweets: List[Tweet] = Field(default_factory=list)


class TimelineResponse(BaseModel):
    data: List[Tweet] = Field(default_factory=list)
    includes: Includes = Field(default_factory=Includes)
    meta: Dict[str, Any] = Field(default_factory=dict)
