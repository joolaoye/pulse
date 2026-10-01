from typing import Protocol


class AudioObjectUpload(Protocol):
    async def write(
        self,
        *,
        content: bytes,
    ) -> None: ...

    async def complete(self) -> int: ...

    async def abort(self) -> None: ...


class AudioObjectStore(Protocol):
    async def begin_upload(
        self,
        *,
        object_key: str,
        content_type: str,
    ) -> AudioObjectUpload: ...
