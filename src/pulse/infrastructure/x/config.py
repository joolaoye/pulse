X_API_BASE_URL = "https://api.x.com/2"

DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0
DEFAULT_LIST_TIMELINE_MAX_RESULTS = 50
DEFAULT_CONVERSATION_MAX_RESULTS = 25
DEFAULT_REPLY_FETCH_MAX_RESULTS = 10


class ClientConfig:
    def __init__(
        self,
        *,
        api_base_url: str = X_API_BASE_URL,
        request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        list_timeline_max_results: int = DEFAULT_LIST_TIMELINE_MAX_RESULTS,
        conversation_max_results: int = DEFAULT_CONVERSATION_MAX_RESULTS,
        reply_fetch_max_results: int = DEFAULT_REPLY_FETCH_MAX_RESULTS,
    ) -> None:
        self.api_base_url = api_base_url
        self.request_timeout_seconds = request_timeout_seconds
        self.list_timeline_max_results = list_timeline_max_results
        self.conversation_max_results = conversation_max_results
        self.reply_fetch_max_results = reply_fetch_max_results
