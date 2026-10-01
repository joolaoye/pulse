import tempfile
from typing import Any, List

from pulse.infrastructure.storage.objects import (
    AudioObjectStore,
    AudioObjectUpload,
)
from pulse.infrastructure.storage.r2.client import R2Client

# R2 rejects non-final multipart parts smaller than 5 MiB. The buffer stays
# at that fixed size instead of growing with the episode.
R2_MULTIPART_PART_BYTES = 5 * 1024 * 1024
R2_UPLOAD_MEMORY_BYTES = R2_MULTIPART_PART_BYTES


class R2AudioObjectStore:
    def __init__(
        self,
        *,
        r2_client: R2Client,
        bucket_name: str,
        max_memory_bytes: int = R2_UPLOAD_MEMORY_BYTES,
    ) -> None:
        if not bucket_name:
            raise ValueError("bucket_name cannot be empty.")

        if max_memory_bytes <= 0:
            raise ValueError("Audio upload memory cap must be positive.")

        self.r2_client = r2_client
        self.bucket_name = bucket_name
        self.max_memory_bytes = max_memory_bytes

    async def begin_upload(
        self,
        *,
        object_key: str,
        content_type: str,
    ) -> AudioObjectUpload:
        return _SpoolingR2Upload(
            r2_client=self.r2_client,
            bucket_name=self.bucket_name,
            object_key=object_key,
            content_type=content_type,
            max_memory_bytes=self.max_memory_bytes,
        )


class WorkerR2AudioObjectStore:
    def __init__(
        self,
        *,
        bucket: Any,
        part_size_bytes: int = R2_MULTIPART_PART_BYTES,
    ) -> None:
        if part_size_bytes <= 0:
            raise ValueError("R2 multipart part size must be positive.")

        self._bucket = bucket
        self._part_size_bytes = part_size_bytes

    async def begin_upload(
        self,
        *,
        object_key: str,
        content_type: str,
    ) -> AudioObjectUpload:
        multipart_upload = await self._bucket.createMultipartUpload(
            object_key,
            {
                "httpMetadata": {
                    "contentType": content_type,
                },
            },
        )

        return _WorkerR2Upload(
            multipart_upload=multipart_upload,
            part_size_bytes=self._part_size_bytes,
        )


def create_audio_object_store(
    *,
    r2_client: R2Client,
    bucket_name: str,
    bucket: Any | None = None,
) -> AudioObjectStore:
    if bucket is not None:
        return WorkerR2AudioObjectStore(
            bucket=bucket,
        )

    return R2AudioObjectStore(
        r2_client=r2_client,
        bucket_name=bucket_name,
    )


class _SpoolingR2Upload:
    def __init__(
        self,
        *,
        r2_client: R2Client,
        bucket_name: str,
        object_key: str,
        content_type: str,
        max_memory_bytes: int,
    ) -> None:
        self._r2_client = r2_client
        self._bucket_name = bucket_name
        self._object_key = object_key
        self._content_type = content_type
        # Closed by _finish when the upload completes or aborts.
        self._spool = tempfile.SpooledTemporaryFile(  # noqa: SIM115
            max_size=max_memory_bytes,
        )
        self._size = 0
        self._finished = False
        self._upload_started = False
        self._committed = False

    async def write(
        self,
        *,
        content: bytes,
    ) -> None:
        self._ensure_open()

        if not content:
            raise ValueError("An audio upload chunk cannot be empty.")

        self._spool.write(content)
        self._size += len(content)

    async def complete(self) -> int:
        self._ensure_open()

        if self._size <= 0:
            raise ValueError("Cannot complete an empty audio upload.")

        self._upload_started = True
        self._spool.seek(0)

        await self._r2_client.upload_object_stream(
            bucket_name=self._bucket_name,
            object_key=self._object_key,
            content=self._spool,
            content_length=self._size,
            content_type=self._content_type,
        )

        self._committed = True
        size = self._size
        self._finish()

        return size

    async def abort(self) -> None:
        if self._finished:
            return

        should_delete = self._upload_started and not self._committed
        self._finish()

        if should_delete:
            await self._r2_client.delete_object(
                bucket_name=self._bucket_name,
                object_key=self._object_key,
            )

    def _ensure_open(self) -> None:
        if self._finished:
            raise RuntimeError("Audio upload is already finished.")

    def _finish(self) -> None:
        self._finished = True
        self._spool.close()


class _WorkerR2Upload:
    def __init__(
        self,
        *,
        multipart_upload: Any,
        part_size_bytes: int,
    ) -> None:
        self._multipart_upload = multipart_upload
        self._part_size_bytes = part_size_bytes
        self._buffer = bytearray()
        self._parts: List[dict[str, Any]] = []
        self._part_number = 1
        self._size = 0
        self._finished = False

    async def write(
        self,
        *,
        content: bytes,
    ) -> None:
        self._ensure_open()

        if not content:
            raise ValueError("An audio upload chunk cannot be empty.")

        self._size += len(content)
        pending = memoryview(content)
        offset = 0

        while offset < len(pending):
            available = self._part_size_bytes - len(self._buffer)
            take = min(available, len(pending) - offset)
            self._buffer.extend(pending[offset : offset + take])
            offset += take

            if len(self._buffer) == self._part_size_bytes:
                await self._flush_buffer()

    async def complete(self) -> int:
        self._ensure_open()

        if self._size <= 0:
            raise ValueError("Cannot complete an empty audio upload.")

        if self._buffer:
            await self._flush_buffer()

        if not self._parts:
            raise RuntimeError("R2 multipart upload produced no parts.")

        await self._multipart_upload.complete(self._parts)
        self._finished = True

        return self._size

    async def abort(self) -> None:
        if self._finished:
            return

        self._finished = True
        self._buffer.clear()
        self._parts.clear()
        await self._multipart_upload.abort()

    async def _flush_buffer(self) -> None:
        payload = bytes(self._buffer)
        self._buffer.clear()
        await self._upload_part(payload)

    async def _upload_part(
        self,
        payload: bytes,
    ) -> None:
        uploaded = await self._multipart_upload.uploadPart(
            self._part_number,
            payload,
        )
        self._parts.append(
            _uploaded_part(
                uploaded=uploaded,
                part_number=self._part_number,
            )
        )
        self._part_number += 1

    def _ensure_open(self) -> None:
        if self._finished:
            raise RuntimeError("Audio upload is already finished.")


def _uploaded_part(
    *,
    uploaded: Any,
    part_number: int,
) -> dict[str, Any]:
    if isinstance(uploaded, dict):
        etag = uploaded.get("etag")
        number = uploaded.get("partNumber", part_number)
    else:
        etag = getattr(uploaded, "etag", None)
        number = getattr(uploaded, "partNumber", part_number)

    if not isinstance(etag, str) or not etag:
        raise RuntimeError("R2 multipart upload did not return a part etag.")

    return {
        "partNumber": int(number),
        "etag": etag,
    }
