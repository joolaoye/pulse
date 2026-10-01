from dataclasses import dataclass
from pathlib import Path

from pulse.application.composition.cloud import (
    CloudflareRestCredentials,
    ProviderCredentials,
    ResourceNames,
)


@dataclass(frozen=True)
class DeploymentInputs:
    wrangler_config_path: Path
    cloudflare: CloudflareRestCredentials
    providers: ProviderCredentials
    resources: ResourceNames
    d1_database_name: str
