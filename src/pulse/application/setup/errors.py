from typing import (
    List,
)


class PulseResourceCollisionError(
    RuntimeError,
):
    def __init__(
        self,
        *,
        resources: List[str],
    ) -> None:
        self.resources = resources

        super().__init__(
            (f"One or more requested Cloudflare resources already exist: {', '.join(resources)}.")
        )


class PulseResourceCompatibilityError(
    RuntimeError,
):
    pass
