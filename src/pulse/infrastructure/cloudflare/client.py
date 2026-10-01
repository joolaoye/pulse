import httpx

from pulse.infrastructure.cloudflare.config import CloudflareConfig


class CloudflareClient:
    def __init__(
        self,
        config: CloudflareConfig,
    ):
        self.config = config
        self.http_client = httpx.AsyncClient(
            base_url=(self.config.api_base_url),
            headers={
                "Authorization": (f"Bearer {self.config.api_token}"),
                "Content-Type": ("application/json"),
            },
            timeout=(self.config.timeout_seconds),
        )

    async def aclose(
        self,
    ) -> None:
        await self.http_client.aclose()
