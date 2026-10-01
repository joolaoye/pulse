from typing import List, Optional

from pydantic import BaseModel, field_validator


class Signal(BaseModel):
    id: str
    source: str
    content: str

    @field_validator(
        "content",
    )
    @classmethod
    def validate_content(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Signal content cannot be empty.")

        return value


class EmbeddedSignal(BaseModel):
    signal_id: str
    embedding: List[float]
    embedding_version: str


class InterestMatch(BaseModel):
    interest_id: str
    title: str
    relevance_score: float


class ScoredSignal(BaseModel):
    signal_id: str
    relevance_score: float
    interest_matches: List[InterestMatch]


class ProcessedSignal(BaseModel):
    signal_id: str
    title: str
    markdown_context: str
    relevance_score: float
    source: str

    def to_llm_string(
        self,
    ) -> str:
        return f"Title:\n{self.title}\n\n{self.markdown_context}"


class StoredSignal(BaseModel):
    signal_id: str
    source: str
    relevance_score: float


class AugmentedXSignal(BaseModel):
    signal_id: str
    author_username: Optional[str] = None
    top_comments: List[str] = []
