from typing import List

import httpx

from pulse.infrastructure.embeddings.voyage.config import VoyageConfig


class VoyageEmbeddingProvider:
    def __init__(
        self,
        config: VoyageConfig,
    ):
        self.config = config

    @property
    def model_name(
        self,
    ) -> str:
        return self.config.embedding_model

    async def embed(
        self,
        text: str,
    ) -> List[float]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ("https://api.voyageai.com/v1/embeddings"),
                headers={
                    "Authorization": (f"Bearer {self.config.api_key}"),
                    "Content-Type": ("application/json"),
                },
                json={
                    "input": [
                        text,
                    ],
                    "model": (self.config.embedding_model),
                    "input_type": ("document"),
                },
            )

            response.raise_for_status()

            payload = response.json()

        return payload["data"][0]["embedding"]
