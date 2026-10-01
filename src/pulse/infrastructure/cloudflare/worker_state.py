from typing import Any, Dict, List

import httpx

from pulse.infrastructure.cloudflare.client import (
    CloudflareClient,
)


class CloudflareWorkerState:
    def __init__(
        self,
        *,
        cloudflare_client: CloudflareClient,
    ) -> None:
        self._cloudflare_client = cloudflare_client

    async def get_settings(
        self,
        *,
        worker_name: str,
    ) -> Dict[str, Any]:
        result = await self._get_result(
            path=self._worker_path(
                worker_name=worker_name,
                suffix="settings",
            ),
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Cloudflare Worker settings response did not contain an object result."
            )

        return result

    async def get_schedules(
        self,
        *,
        worker_name: str,
    ) -> List[Dict[str, Any]]:
        result = await self._get_result(
            path=self._worker_path(
                worker_name=worker_name,
                suffix="schedules",
            ),
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Cloudflare Worker schedules response did not contain an object result."
            )

        schedules = result.get("schedules")

        if not isinstance(schedules, list):
            raise RuntimeError(
                "Cloudflare Worker schedules response did not contain a schedules list."
            )

        return schedules

    async def list_secrets(
        self,
        *,
        worker_name: str,
    ) -> List[Dict[str, Any]]:
        result = await self._get_result(
            path=self._worker_path(
                worker_name=worker_name,
                suffix="secrets",
            ),
        )

        if not isinstance(result, list):
            raise RuntimeError("Cloudflare Worker secrets response did not contain a list result.")

        return result

    async def list_deployments(
        self,
        *,
        worker_name: str,
    ) -> List[Dict[str, Any]]:
        result = await self._get_result(
            path=self._worker_path(
                worker_name=worker_name,
                suffix="deployments",
            ),
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Cloudflare Worker deployments response did not contain an object result."
            )

        deployments = result.get("deployments")

        if not isinstance(deployments, list):
            raise RuntimeError(
                "Cloudflare Worker deployments response did not contain a deployments list."
            )

        return deployments

    async def _get_result(
        self,
        *,
        path: str,
    ) -> Any:
        try:
            response = await self._cloudflare_client.http_client.get(path)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise RuntimeError(f"Cloudflare Worker state request failed. Path: {path}") from error

        try:
            payload = response.json()
        except ValueError as error:
            raise RuntimeError("Cloudflare Worker state response was not valid JSON.") from error

        if not isinstance(payload, dict):
            raise RuntimeError("Cloudflare Worker state response was not a JSON object.")

        if payload.get("success") is not True:
            raise RuntimeError("Cloudflare Worker state request was not successful.")

        if "result" not in payload:
            raise RuntimeError("Cloudflare Worker state response did not contain a result.")

        return payload["result"]

    def _worker_path(
        self,
        *,
        worker_name: str,
        suffix: str,
    ) -> str:
        return (
            f"/accounts/"
            f"{self._cloudflare_client.config.account_id}"
            f"/workers/scripts/"
            f"{worker_name}/"
            f"{suffix}"
        )
