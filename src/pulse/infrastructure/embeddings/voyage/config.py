DEFAULT_EMBEDDING_MODEL = "voyage-4"


class VoyageConfig:
    def __init__(
        self,
        *,
        api_key: str,
        embedding_model: str = (DEFAULT_EMBEDDING_MODEL),
    ):
        self.api_key = api_key
        self.embedding_model = embedding_model
