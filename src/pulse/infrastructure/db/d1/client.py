from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
)

from pulse.infrastructure.cloudflare import CloudflareClient
from pulse.infrastructure.db.d1.config import (
    CLOUDFLARE_D1_DATABASE_QUERY_ENDPOINT,
    D1Config,
)


class DatabaseClient(Protocol):
    async def query(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> List[Dict[str, Any]]: ...

    async def execute(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> None: ...


class D1Client:
    def __init__(
        self,
        cloudflare_client: CloudflareClient,
        config: D1Config,
    ):
        self.cloudflare_client = cloudflare_client

        self.config = config

    async def query(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> List[
        Dict[
            str,
            Any,
        ]
    ]:
        query_result = await self._execute_query(
            sql=sql,
            params=params,
        )

        results = query_result.get("results")

        if not results:
            return []

        if not isinstance(
            results,
            list,
        ):
            raise ValueError(("Cloudflare D1 returned invalid query results."))

        return results

    async def execute(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> None:
        await self._execute_query(
            sql=sql,
            params=params,
        )

    async def _execute_query(
        self,
        *,
        sql: str,
        params: Optional[Sequence[Any]],
    ) -> Dict[str, Any]:
        endpoint = CLOUDFLARE_D1_DATABASE_QUERY_ENDPOINT.format(
            account_id=self.cloudflare_client.config.account_id,
            database_id=self.config.database_id,
        )

        request_body: Dict[str, Any] = {
            "sql": sql,
        }

        if params is not None:
            request_body["params"] = list(params)

        response = await self.cloudflare_client.http_client.post(
            endpoint,
            json=request_body,
        )

        if response.is_error:
            raise RuntimeError(
                "Cloudflare D1 request failed. "
                f"Method: {response.request.method}. "
                f"URL: {response.request.url}. "
                f"Status: {response.status_code}. "
                f"Response: {response.text}"
            )

        payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError("Cloudflare D1 returned an invalid response.")

        if payload.get("success") is not True:
            raise RuntimeError(f"Cloudflare D1 query was unsuccessful: {payload.get('errors', [])}")

        result = payload.get("result")

        if not isinstance(result, list):
            raise ValueError("Cloudflare D1 returned an invalid result payload.")

        if not result:
            return {}

        query_result = result[0]

        if not isinstance(query_result, dict):
            raise ValueError("Cloudflare D1 returned an invalid query result.")

        if query_result.get("success") is False:
            raise RuntimeError(f"Cloudflare D1 query execution failed: {query_result}")

        return query_result
