from enum import StrEnum


class NoContentReason(StrEnum):
    NO_UNSEEN_SIGNALS = "no_unseen_signals"
    NO_SEMANTICALLY_UNIQUE_SIGNALS = "no_semantically_unique_signals"
    NO_PROCESSED_SIGNALS = "no_processed_signals"
    NO_THEMED_CLUSTERS = "no_themed_clusters"


class WorkflowOutcome(StrEnum):
    PUBLISHED = "published"
    NO_CONTENT = "no_content"
