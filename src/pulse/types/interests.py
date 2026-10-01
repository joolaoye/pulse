from typing import List

from pydantic import BaseModel


class InterestChunk(BaseModel):
    title: str
    content: str


class EmbeddedInterest(BaseModel):
    interest_id: str
    title: str
    content: str
    embedding: List[float]
    embedding_version: str
