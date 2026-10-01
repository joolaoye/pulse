from pulse.infrastructure.db import XDiscourseCacheRepository
from pulse.infrastructure.db.d1 import D1Client
from pulse.infrastructure.x import XClient
from pulse.services.retrieval import (
    DiscourseReconstructor,
    XRetriever,
)


def create_x_retriever(
    *,
    x_client: XClient,
    d1_client: D1Client,
) -> XRetriever:
    return XRetriever(
        client=x_client,
        cache_repository=XDiscourseCacheRepository(
            db_client=d1_client,
        ),
        discourse_reconstructor=DiscourseReconstructor(),
    )
