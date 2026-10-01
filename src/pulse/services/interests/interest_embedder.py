import re
from typing import List, Tuple
import uuid

from pulse.infrastructure.embeddings import VoyageEmbeddingProvider
from pulse.types import EmbeddedInterest


def _parse_interest_markdown(
    markdown: str,
) -> List[Tuple[str, str]]:
    chunks: List[Tuple[str, str]] = []

    for section in re.split(r"^#\s+", markdown, flags=re.MULTILINE):
        section = section.strip()

        if not section:
            continue

        lines = section.splitlines()
        title = lines[0].strip()
        content = "\n".join(lines[1:]).strip()

        if content:
            chunks.append((title, content))

    return chunks


class InterestEmbedder:
    def __init__(
        self,
        *,
        embedding_provider: VoyageEmbeddingProvider,
    ) -> None:
        self.embedding_provider = embedding_provider

    async def embed_markdown(
        self,
        markdown: str,
    ) -> List[EmbeddedInterest]:
        embedded_interests: List[EmbeddedInterest] = []

        for title, content in _parse_interest_markdown(markdown):
            embedded_interests.append(
                EmbeddedInterest(
                    interest_id=str(uuid.uuid4()),
                    title=title,
                    content=content,
                    embedding=await self.embedding_provider.embed(content),
                    embedding_version=self.embedding_provider.model_name,
                )
            )

        return embedded_interests
