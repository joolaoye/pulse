from typing import List

from pydantic import BaseModel, Field


class Theme(BaseModel):
    title: str = Field(
        ...,
        description=(
            "A concise title capturing the overarching trend shared by the provided "
            "signals. It should describe the broader movement or shift rather than "
            "individual companies, products, or isolated events. This title serves "
            "as the theme's primary identifier throughout subsequent generation stages."
        ),
    )
    summary: str = Field(
        ...,
        description=(
            "A concise explanation of why the provided signals belong together and "
            "what broader technological, market, or behavioral trend they collectively "
            "represent. It should synthesize across the signals rather than summarize "
            "them individually and provide context for downstream planning."
        ),
    )

    def to_llm_string(self) -> str:
        return f"# Theme\n\nTitle:\n{self.title}\n\nSummary:\n{self.summary}"


class SignalCluster(BaseModel):
    cluster_id: int
    signal_ids: List[str] = Field(..., min_length=1)


class ThemedSignalCluster(BaseModel):
    cluster_id: int
    relevance_score: float
    theme: Theme
    signal_ids: List[str] = Field(..., min_length=1)
