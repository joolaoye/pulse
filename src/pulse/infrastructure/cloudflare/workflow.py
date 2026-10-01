from datetime import (
    datetime,
    timezone,
)
from hashlib import sha256

SCHEDULED_WORKFLOW_ID_PREFIX = "scheduled-"


def build_scheduled_workflow_id(
    *,
    pipeline_id: str,
    scheduled_for: datetime,
) -> str:
    pipeline_id = pipeline_id.strip()

    if not pipeline_id:
        raise ValueError("Podcast pipeline ID cannot be empty.")

    if scheduled_for.tzinfo is None or scheduled_for.utcoffset() is None:
        raise ValueError("Scheduled occurrence must be timezone-aware.")

    scheduled_for_utc = (
        scheduled_for.astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace(
            "+00:00",
            "Z",
        )
    )

    occurrence_identity = f"pulse-scheduled-v1:{len(pipeline_id)}:{pipeline_id}:{scheduled_for_utc}"

    digest = sha256(occurrence_identity.encode("utf-8")).hexdigest()

    return f"{SCHEDULED_WORKFLOW_ID_PREFIX}{digest}"
