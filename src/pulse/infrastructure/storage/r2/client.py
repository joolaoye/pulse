from typing import AsyncIterator, Protocol

from pulse.infrastructure.cloudflare import CloudflareClient

DEFAULT_UPLOAD_TIMEOUT_SECONDS = 60.0
DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 120.0
_STREAM_READ_BYTES = 64 * 1024
_MINIMUM_STREAM_BYTES_PER_SECOND = 128 * 1024


class _ByteReader(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...


class R2Client:
    def __init__(
        self,
        *,
        cloudflare_client: CloudflareClient,
        upload_timeout_seconds: float = DEFAULT_UPLOAD_TIMEOUT_SECONDS,
        download_timeout_seconds: float = DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
    ) -> None:
        if upload_timeout_seconds <= 0:
            raise ValueError("R2 upload timeout must be positive.")

        if download_timeout_seconds <= 0:
            raise ValueError("R2 download timeout must be positive.")

        self.cloudflare_client = cloudflare_client
        self.upload_timeout_seconds = upload_timeout_seconds
        self.download_timeout_seconds = download_timeout_seconds

    async def upload_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        response = await self.cloudflare_client.http_client.put(
            self._object_path(
                bucket_name=bucket_name,
                object_key=object_key,
            ),
            content=content,
            headers={
                "Content-Type": content_type,
            },
            timeout=self.upload_timeout_seconds,
        )

        response.raise_for_status()

    async def upload_object_stream(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content: _ByteReader,
        content_length: int,
        content_type: str,
    ) -> None:
        if content_length <= 0:
            raise ValueError("R2 streamed uploads require a positive content length.")

        async def chunks() -> AsyncIterator[bytes]:
            while True:
                chunk = content.read(_STREAM_READ_BYTES)

                if not chunk:
                    return

                yield chunk

        response = await self.cloudflare_client.http_client.put(
            self._object_path(
                bucket_name=bucket_name,
                object_key=object_key,
            ),
            content=chunks(),
            headers={
                "Content-Type": content_type,
                "Content-Length": str(content_length),
            },
            timeout=max(
                self.upload_timeout_seconds,
                content_length / _MINIMUM_STREAM_BYTES_PER_SECOND,
            ),
        )

        response.raise_for_status()

    async def download_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> bytes:
        response = await self.cloudflare_client.http_client.get(
            self._object_path(
                bucket_name=bucket_name,
                object_key=object_key,
            ),
            timeout=self.download_timeout_seconds,
        )

        response.raise_for_status()

        return response.content

    async def delete_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> None:
        response = await self.cloudflare_client.http_client.delete(
            self._object_path(
                bucket_name=bucket_name,
                object_key=object_key,
            )
        )

        response.raise_for_status()

    def _object_path(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> str:
        return (
            f"/accounts/{self.cloudflare_client.config.account_id}"
            f"/r2/buckets/{bucket_name}"
            f"/objects/{object_key}"
        )
