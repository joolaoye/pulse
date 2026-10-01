from typing import List

from pydantic import BaseModel, Field

from pulse.types import ProcessedSignal


class ThemeExtractionInput(BaseModel):
    signals: List[ProcessedSignal] = Field(
        ...,
        min_length=1,
        description=(
            "A collection of semantically related processed signals that were "
            "previously grouped into the same cluster. Together, these signals "
            "represent multiple pieces of evidence describing a common emerging "
            "trend. The agent should synthesize across the entire collection rather "
            "than analyzing each signal independently."
        ),
    )

    def to_llm_string(self) -> str:
        return "\n\n---\n\n".join(signal.to_llm_string() for signal in self.signals)
