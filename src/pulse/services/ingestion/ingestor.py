from typing import List

from pulse.services.ingestion.canonicalizer import XCanonicalizer
from pulse.services.ingestion.exact_deduplicator import ExactDeduplicator
from pulse.types import Discourse, Signal


class Ingestor:
    def __init__(
        self,
        *,
        exact_deduplicator: ExactDeduplicator,
    ) -> None:
        self.exact_deduplicator = exact_deduplicator

    async def ingest(
        self,
        *,
        reconstructed_discourses: List[Discourse],
    ) -> List[Signal]:
        unseen_signals: List[Signal] = []

        seen_identities: set[tuple[str, str]] = set()

        for discourse in reconstructed_discourses:
            signal = XCanonicalizer.canonicalize(
                discourse=discourse,
            )

            identity = (
                signal.source,
                signal.id,
            )

            if identity in seen_identities:
                continue

            seen_identities.add(identity)

            exists = await self.exact_deduplicator.exists(
                signal=signal,
            )

            if exists:
                continue

            unseen_signals.append(signal)

        return unseen_signals
