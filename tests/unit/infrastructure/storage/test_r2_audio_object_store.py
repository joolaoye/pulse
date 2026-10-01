import io
from typing import Any, List

import httpx
import pytest

from pulse.infrastructure.cloudflare import CloudflareClient, CloudflareConfig
from pulse.infrastructure.storage.r2.client import R2Client
from pulse.infrastructure.storage.r2.object_store import (
    R2AudioObjectStore,
    WorkerR2AudioObjectStore,
)


class FakeMultipartUpload:
    def __init__(self) -> None:
        self.parts: List[tuple[int, bytes]] = []
        self.completed: List[dict[str, Any]] | None = None
        self.aborted = False

    async def uploadPart(
        self,
        part_number: int,
        content: bytes,
    ) -> dict[str, Any]:
        self.parts.append((part_number, bytes(content)))

        return {
            "partNumber": part_number,
            "etag": f"etag-{part_number}",
        }

    async def complete(
        self,
        parts: List[dict[str, Any]],
    ) -> None:
        self.completed = parts

    async def abort(self) -> None:
        self.aborted = True


class FakeBucket:
    def __init__(self) -> None:
        self.created: List[tuple[str, dict[str, Any]]] = []
        self.upload = FakeMultipartUpload()

    async def createMultipartUpload(
        self,
        object_key: str,
        options: dict[str, Any],
    ) -> FakeMultipartUpload:
        self.created.append((object_key, options))

        return self.upload


class FakeR2Client:
    def __init__(
        self,
        *,
        fail_upload: bool = False,
    ) -> None:
        self.fail_upload = fail_upload
        self.streams: List[dict[str, Any]] = []
        self.deleted: List[tuple[str, str]] = []

    async def upload_object_stream(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content: Any,
        content_length: int,
        content_type: str,
    ) -> None:
        if self.fail_upload:
            raise RuntimeError("stream upload failed")

        chunks: List[bytes] = []

        while True:
            chunk = content.read(8)

            if not chunk:
                break

            chunks.append(chunk)

        self.streams.append(
            {
                "bucket_name": bucket_name,
                "object_key": object_key,
                "content_type": content_type,
                "content_length": content_length,
                "body": b"".join(chunks),
                "received_bytes": not isinstance(content, (bytes, bytearray)),
            }
        )

    async def delete_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> None:
        self.deleted.append((bucket_name, object_key))


async def test_worker_upload_flushes_fixed_size_parts_without_keeping_the_episode() -> None:
    bucket = FakeBucket()
    store = WorkerR2AudioObjectStore(
        bucket=bucket,
        part_size_bytes=4,
    )
    upload = await store.begin_upload(
        object_key="shows/show-1/episodes/episode-1/audio.mp3",
        content_type="audio/mpeg",
    )

    await upload.write(content=b"abcdefghij")
    await upload.write(content=b"XYZ")

    assert len(bucket.upload.parts) == 3
    assert all(len(part) == 4 for _, part in bucket.upload.parts)
    assert len(upload._buffer) < 4  # type: ignore[attr-defined]

    size = await upload.complete()

    assert size == 13
    assert [part for _, part in bucket.upload.parts] == [
        b"abcd",
        b"efgh",
        b"ijXY",
        b"Z",
    ]
    assert bucket.upload.completed == [
        {"partNumber": 1, "etag": "etag-1"},
        {"partNumber": 2, "etag": "etag-2"},
        {"partNumber": 3, "etag": "etag-3"},
        {"partNumber": 4, "etag": "etag-4"},
    ]
    assert bucket.created == [
        (
            "shows/show-1/episodes/episode-1/audio.mp3",
            {"httpMetadata": {"contentType": "audio/mpeg"}},
        )
    ]
    assert upload._buffer == bytearray()  # type: ignore[attr-defined]
    assert all(isinstance(part["etag"], str) for part in upload._parts)  # type: ignore[attr-defined]


class _PeakBytearray(bytearray):
    def __init__(self) -> None:
        super().__init__()
        self.peak = 0

    def extend(self, iterable: Any) -> None:
        super().extend(iterable)
        self.peak = max(self.peak, len(self))


class _ObservingMultipartUpload(FakeMultipartUpload):
    def __init__(self) -> None:
        super().__init__()
        self.owner: Any = None
        self.buffer_lengths: List[int] = []
        self.payload_lengths: List[int] = []

    async def uploadPart(
        self,
        part_number: int,
        content: bytes,
    ) -> dict[str, Any]:
        self.buffer_lengths.append(len(self.owner._buffer))
        self.payload_lengths.append(len(content))

        return await super().uploadPart(part_number, content)


def _audio_lengths(value: Any) -> List[int]:
    if isinstance(value, (bytes, bytearray)):
        return [len(value)]

    if isinstance(value, dict):
        return [length for nested in value.values() for length in _audio_lengths(nested)]

    if isinstance(value, list):
        return [length for item in value for length in _audio_lengths(item)]

    return []


def _retained_audio_lengths(upload: Any) -> List[int]:
    lengths: List[int] = []

    for name, value in vars(upload).items():
        if name == "_multipart_upload":
            continue

        lengths.extend(_audio_lengths(value))

    return lengths


async def test_worker_buffer_stays_within_one_part_across_many_chunks() -> None:
    part_size = 8
    bucket = FakeBucket()
    observing = _ObservingMultipartUpload()
    bucket.upload = observing
    store = WorkerR2AudioObjectStore(
        bucket=bucket,
        part_size_bytes=part_size,
    )
    upload = await store.begin_upload(
        object_key="shows/show-1/episodes/episode-1/audio.mp3",
        content_type="audio/mpeg",
    )
    buffer = _PeakBytearray()
    upload._buffer = buffer  # type: ignore[attr-defined]
    observing.owner = upload
    chunks = [bytes([index % 251]) * ((index % 5) + 1) for index in range(80)]
    chunks.append(b"Q" * ((part_size * 3) + 5))
    chunks.append(b"\xff")
    written = 0

    for chunk in chunks:
        await upload.write(content=chunk)
        written += len(chunk)

        assert buffer.peak <= part_size + len(chunk)
        assert buffer.peak <= part_size
        assert len(buffer) < part_size
        assert upload._size == written  # type: ignore[attr-defined]
        retained = [length for length in _retained_audio_lengths(upload) if length]
        assert retained == ([len(buffer)] if buffer else [])
        assert all(  # type: ignore[attr-defined]
            isinstance(part["etag"], str) and isinstance(part["partNumber"], int)
            for part in upload._parts  # type: ignore[attr-defined]
        )

    episode = b"".join(chunks)

    assert written > part_size * 10
    assert len(episode) == written
    assert all(part != episode for _, part in observing.parts)
    assert all(length == 0 for length in observing.buffer_lengths)
    assert all(length == part_size for length in observing.payload_lengths)

    size = await upload.complete()
    final_part = observing.parts[-1][1]

    assert size == written
    assert 0 < len(final_part) < part_size
    assert all(len(part) == part_size for _, part in observing.parts[:-1])
    assert upload._buffer == bytearray()  # type: ignore[attr-defined]
    assert _retained_audio_lengths(upload) == [0]
    assert all(
        set(part) == {"partNumber", "etag"} and isinstance(part["etag"], str)
        for part in upload._parts  # type: ignore[attr-defined]
    )


async def test_worker_abort_is_forwarded_without_completing_parts() -> None:
    bucket = FakeBucket()
    store = WorkerR2AudioObjectStore(
        bucket=bucket,
        part_size_bytes=4,
    )
    upload = await store.begin_upload(
        object_key="audio.mp3",
        content_type="audio/mpeg",
    )

    await upload.write(content=b"abc")
    await upload.abort()

    assert bucket.upload.aborted is True
    assert bucket.upload.completed is None
    assert bucket.upload.parts == []


async def test_rest_upload_spools_past_the_memory_cap_and_streams_on_complete() -> None:
    client = FakeR2Client()
    store = R2AudioObjectStore(
        r2_client=client,  # type: ignore[arg-type]
        bucket_name="podcast-bucket",
        max_memory_bytes=8,
    )
    upload = await store.begin_upload(
        object_key="shows/show-1/episodes/episode-1/audio.mp3",
        content_type="audio/mpeg",
    )

    await upload.write(content=b"12345")
    await upload.write(content=b"67890abcde")

    spool = upload._spool  # type: ignore[attr-defined]
    assert spool._rolled is True
    assert not isinstance(spool._file, io.BytesIO)
    assert client.streams == []

    size = await upload.complete()

    assert size == 15
    assert client.streams == [
        {
            "bucket_name": "podcast-bucket",
            "object_key": "shows/show-1/episodes/episode-1/audio.mp3",
            "content_type": "audio/mpeg",
            "content_length": 15,
            "body": b"1234567890abcde",
            "received_bytes": True,
        }
    ]
    assert client.deleted == []


async def test_rest_abort_before_upload_does_not_delete_an_object() -> None:
    client = FakeR2Client()
    store = R2AudioObjectStore(
        r2_client=client,  # type: ignore[arg-type]
        bucket_name="podcast-bucket",
        max_memory_bytes=8,
    )
    upload = await store.begin_upload(
        object_key="audio.mp3",
        content_type="audio/mpeg",
    )

    await upload.write(content=b"partial")
    await upload.abort()

    assert client.streams == []
    assert client.deleted == []


async def test_rest_abort_after_a_failed_upload_deletes_the_object() -> None:
    client = FakeR2Client(fail_upload=True)
    store = R2AudioObjectStore(
        r2_client=client,  # type: ignore[arg-type]
        bucket_name="podcast-bucket",
    )
    upload = await store.begin_upload(
        object_key="shows/show-1/episodes/episode-1/audio.mp3",
        content_type="audio/mpeg",
    )
    await upload.write(content=b"audio")

    with pytest.raises(RuntimeError, match="stream upload failed"):
        await upload.complete()

    await upload.abort()

    assert client.deleted == [
        ("podcast-bucket", "shows/show-1/episodes/episode-1/audio.mp3"),
    ]


async def test_upload_object_stream_sends_a_content_length_without_buffering_first() -> None:
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = await request.aread()
        captured["headers"] = request.headers
        captured["url"] = str(request.url)

        return httpx.Response(200)

    cloudflare = CloudflareClient(
        config=CloudflareConfig(
            api_token="token",
            account_id="account-1",
        ),
    )
    await cloudflare.http_client.aclose()
    cloudflare.http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://example.test",
    )
    client = R2Client(cloudflare_client=cloudflare)
    payload = b"streamed-audio-bytes"

    try:
        await client.upload_object_stream(
            bucket_name="podcast-bucket",
            object_key="shows/show-1/episodes/episode-1/audio.mp3",
            content=io.BytesIO(payload),
            content_length=len(payload),
            content_type="audio/mpeg",
        )
    finally:
        await cloudflare.http_client.aclose()

    assert captured["body"] == payload
    assert captured["headers"]["content-length"] == str(len(payload))
    assert captured["headers"]["content-type"] == "audio/mpeg"
    assert "chunked" not in captured["headers"].get("transfer-encoding", "")
    assert captured["url"].endswith(
        "/accounts/account-1/r2/buckets/podcast-bucket/objects/shows/show-1/episodes/episode-1/audio.mp3"
    )
