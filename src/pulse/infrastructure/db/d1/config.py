from uuid import UUID

DEFAULT_D1_QUERY_TIMEOUT_SECONDS = 30.0
DEFAULT_D1_MAX_RETRIES = 3
DEFAULT_D1_RETRY_BACKOFF_SECONDS = 1.0
CLOUDFLARE_D1_DATABASE_QUERY_ENDPOINT = "/accounts/{account_id}/d1/database/{database_id}/query"


class D1Config:
    def __init__(
        self,
        *,
        database_id: str,
        query_timeout_seconds: float = (DEFAULT_D1_QUERY_TIMEOUT_SECONDS),
        max_retries: int = (DEFAULT_D1_MAX_RETRIES),
        retry_backoff_seconds: float = (DEFAULT_D1_RETRY_BACKOFF_SECONDS),
    ):
        try:
            self.database_id = str(UUID(database_id.strip()))

        except ValueError as error:
            raise ValueError(
                (
                    "D1 database_id must be a valid "
                    "UUID. "
                    f"Received length: "
                    f"{len(database_id.strip())}."
                )
            ) from error

        self.query_timeout_seconds = query_timeout_seconds

        self.max_retries = max_retries

        self.retry_backoff_seconds = retry_backoff_seconds
