from typing import (
    Any,
    Dict,
    Optional,
)

import httpx

from pulse.infrastructure.cloudflare.client import CloudflareClient


class CloudflareProvisioner:
    def __init__(
        self,
        *,
        cloudflare_client: CloudflareClient,
    ) -> None:
        self.cloudflare_client = cloudflare_client

    def _build_account_endpoint(
        self,
        *,
        endpoint: str,
    ) -> str:
        return f"/accounts/{self.cloudflare_client.config.account_id}{endpoint}"

    async def get_d1_database(
        self,
        *,
        database_name: str,
    ) -> Optional[
        Dict[
            str,
            Any,
        ]
    ]:
        response = await self.cloudflare_client.http_client.get(
            self._build_account_endpoint(
                endpoint=("/d1/database"),
            ),
            params={
                "name": database_name,
            },
        )

        response.raise_for_status()

        payload = response.json()

        databases = payload.get(
            "result",
            [],
        )

        for database in databases:
            if database.get("name") == database_name:
                return database

        return None

    async def create_d1_database(
        self,
        *,
        database_name: str,
    ) -> Dict[
        str,
        Any,
    ]:
        response = await self.cloudflare_client.http_client.post(
            self._build_account_endpoint(
                endpoint=("/d1/database"),
            ),
            json={
                "name": database_name,
            },
        )

        response.raise_for_status()

        payload = response.json()

        return payload["result"]

    async def get_r2_bucket(
        self,
        *,
        bucket_name: str,
    ) -> Optional[
        Dict[
            str,
            Any,
        ]
    ]:
        endpoint = f"/r2/buckets/{bucket_name}"

        try:
            response = await self.cloudflare_client.http_client.get(
                self._build_account_endpoint(
                    endpoint=endpoint,
                )
            )

            response.raise_for_status()

        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return None

            raise

        payload = response.json()

        return payload["result"]

    async def create_r2_bucket(
        self,
        *,
        bucket_name: str,
    ) -> Dict[
        str,
        Any,
    ]:
        response = await self.cloudflare_client.http_client.post(
            self._build_account_endpoint(
                endpoint=("/r2/buckets"),
            ),
            json={
                "name": bucket_name,
            },
        )

        response.raise_for_status()

        payload = response.json()

        return payload["result"]
