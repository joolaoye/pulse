import json
from typing import Any, Dict, List, Optional

from httpx import HTTPStatusError

from pulse.infrastructure.cloudflare import CloudflareClient

VECTORIZE_INDEXES_ENDPOINT = "/vectorize/v2/indexes"
VECTORIZE_SINGLE_INDEX_ENDPOINT = "/vectorize/v2/indexes/{index_name}"
VECTORIZE_UPSERT_ENDPOINT = "/vectorize/v2/indexes/{index_name}/upsert"
VECTORIZE_QUERY_ENDPOINT = "/vectorize/v2/indexes/{index_name}/query"
VECTORIZE_GET_BY_IDS_ENDPOINT = "/vectorize/v2/indexes/{index_name}/get_by_ids"
VECTORIZE_DELETE_BY_IDS_ENDPOINT = "/vectorize/v2/indexes/{index_name}/delete_by_ids"
VECTORIZE_INDEX_INFO_ENDPOINT = "/vectorize/v2/indexes/{index_name}/info"
VECTORIZE_METADATA_INDEX_LIST_ENDPOINT = "/vectorize/v2/indexes/{index_name}/metadata_index/list"
VECTORIZE_METADATA_INDEX_CREATE_ENDPOINT = (
    "/vectorize/v2/indexes/{index_name}/metadata_index/create"
)

VECTORIZE_NDJSON_CONTENT_TYPE = "application/x-ndjson"
VECTORIZE_JSON_CONTENT_TYPE = "application/json"
VECTORIZE_DEFAULT_METRIC = "cosine"


class VectorizeClient:
    def __init__(
        self,
        *,
        cloudflare_client: CloudflareClient,
    ) -> None:
        self.cloudflare_client = cloudflare_client

    async def create_index(
        self,
        *,
        index_name: str,
        dimensions: int,
        metric: str = VECTORIZE_DEFAULT_METRIC,
        description: str = "",
    ) -> Dict[str, Any]:
        response = await self.cloudflare_client.http_client.post(
            self._build_account_endpoint(VECTORIZE_INDEXES_ENDPOINT),
            headers=self._json_headers(),
            json={
                "name": index_name,
                "description": description,
                "config": {
                    "dimensions": dimensions,
                    "metric": metric,
                },
            },
        )

        response.raise_for_status()
        return response.json()["result"]

    async def get_index(
        self,
        *,
        index_name: str,
    ) -> Dict[str, Any]:
        response = await self.cloudflare_client.http_client.get(
            self._build_index_endpoint(
                VECTORIZE_SINGLE_INDEX_ENDPOINT,
                index_name=index_name,
            )
        )

        response.raise_for_status()
        return response.json()["result"]

    async def list_indexes(self) -> List[Dict[str, Any]]:
        response = await self.cloudflare_client.http_client.get(
            self._build_account_endpoint(VECTORIZE_INDEXES_ENDPOINT)
        )

        response.raise_for_status()
        return response.json()["result"]

    async def index_exists(
        self,
        *,
        index_name: str,
    ) -> bool:
        try:
            await self.get_index(index_name=index_name)
            return True
        except HTTPStatusError as error:
            if error.response.status_code == 404:
                return False

            raise

    async def get_index_info(
        self,
        *,
        index_name: str,
    ) -> Dict[str, Any]:
        response = await self.cloudflare_client.http_client.get(
            self._build_index_endpoint(
                VECTORIZE_INDEX_INFO_ENDPOINT,
                index_name=index_name,
            )
        )

        response.raise_for_status()
        return response.json()["result"]

    async def list_metadata_indexes(
        self,
        *,
        index_name: str,
    ) -> List[Dict[str, Any]]:
        response = await self.cloudflare_client.http_client.get(
            self._build_index_endpoint(
                VECTORIZE_METADATA_INDEX_LIST_ENDPOINT,
                index_name=index_name,
            )
        )

        response.raise_for_status()

        result = response.json().get("result", {})
        return result.get("metadataIndexes", [])

    async def create_metadata_index(
        self,
        *,
        index_name: str,
        property_name: str,
        index_type: str,
    ) -> Dict[str, Any]:
        response = await self.cloudflare_client.http_client.post(
            self._build_index_endpoint(
                VECTORIZE_METADATA_INDEX_CREATE_ENDPOINT,
                index_name=index_name,
            ),
            headers=self._json_headers(),
            json={
                "propertyName": property_name,
                "indexType": index_type,
            },
        )

        response.raise_for_status()
        return response.json()["result"]

    async def upsert_vector(
        self,
        *,
        index_name: str,
        vector_id: str,
        values: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        vector_payload: Dict[str, Any] = {
            "id": vector_id,
            "values": values,
        }

        if metadata:
            vector_payload["metadata"] = metadata

        response = await self.cloudflare_client.http_client.post(
            self._build_index_endpoint(
                VECTORIZE_UPSERT_ENDPOINT,
                index_name=index_name,
            ),
            headers={
                "Content-Type": VECTORIZE_NDJSON_CONTENT_TYPE,
            },
            content=f"{json.dumps(vector_payload)}\n",
        )

        response.raise_for_status()
        return response.json()["result"]

    async def query_vector(
        self,
        *,
        index_name: str,
        vector: List[float],
        top_k: int,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        request_payload: Dict[str, Any] = {
            "vector": vector,
            "topK": top_k,
            "returnMetadata": "all",
            "returnValues": False,
        }

        if metadata_filter:
            request_payload["filter"] = metadata_filter

        response = await self.cloudflare_client.http_client.post(
            self._build_index_endpoint(
                VECTORIZE_QUERY_ENDPOINT,
                index_name=index_name,
            ),
            headers=self._json_headers(),
            json=request_payload,
        )

        response.raise_for_status()
        return response.json()["result"]["matches"]

    async def get_vectors_by_ids(
        self,
        *,
        index_name: str,
        vector_ids: List[str],
    ) -> List[Dict[str, Any]]:
        response = await self.cloudflare_client.http_client.post(
            self._build_index_endpoint(
                VECTORIZE_GET_BY_IDS_ENDPOINT,
                index_name=index_name,
            ),
            headers=self._json_headers(),
            json={"ids": vector_ids},
        )

        response.raise_for_status()
        return response.json().get("result", [])

    async def delete_vector(
        self,
        *,
        index_name: str,
        vector_id: str,
    ) -> Dict[str, Any]:
        response = await self.cloudflare_client.http_client.post(
            self._build_index_endpoint(
                VECTORIZE_DELETE_BY_IDS_ENDPOINT,
                index_name=index_name,
            ),
            headers=self._json_headers(),
            json={"ids": [vector_id]},
        )

        response.raise_for_status()
        return response.json()["result"]

    def _build_account_endpoint(
        self,
        endpoint: str,
    ) -> str:
        return f"/accounts/{self.cloudflare_client.config.account_id}{endpoint}"

    def _build_index_endpoint(
        self,
        endpoint: str,
        *,
        index_name: str,
    ) -> str:
        return self._build_account_endpoint(endpoint.format(index_name=index_name))

    @staticmethod
    def _json_headers() -> Dict[str, str]:
        return {
            "Content-Type": VECTORIZE_JSON_CONTENT_TYPE,
        }
