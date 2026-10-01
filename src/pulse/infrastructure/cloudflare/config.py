CLOUDFLARE_API_BASE_URL = "https://api.cloudflare.com/client/v4"
DEFAULT_CLOUDFLARE_TIMEOUT_SECONDS = 30.0
DEFAULT_CLOUDFLARE_MAX_RETRIES = 3


class CloudflareConfig:
    def __init__(
        self,
        *,
        api_token: str,
        account_id: str,
        api_base_url: str = (CLOUDFLARE_API_BASE_URL),
        timeout_seconds: float = (DEFAULT_CLOUDFLARE_TIMEOUT_SECONDS),
        max_retries: int = (DEFAULT_CLOUDFLARE_MAX_RETRIES),
    ):
        self.api_token = api_token
        self.account_id = account_id
        self.api_base_url = api_base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
