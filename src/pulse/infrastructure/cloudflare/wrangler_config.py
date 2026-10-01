from pathlib import Path
from typing import Dict, Tuple

WRANGLER_TEMPLATE_PATH = Path("workers/cloudflare/wrangler.jsonc.template")
WRANGLER_CONFIG_PATH = Path("workers/cloudflare/wrangler.jsonc")

WORKER_NAME = "pulse-worker"
WORKER_MAIN = "entrypoint.py"

WORKFLOW_BINDING = "PULSE_PIPELINE_WORKFLOW"
WORKFLOW_CLASS = "PulsePipelineWorkflow"
WORKFLOW_NAME = "pulse-pipeline"

D1_BINDING = "PULSE_DB"

SCHEDULER_CRON = "*/5 * * * *"

REQUIRED_COMPATIBILITY_FLAGS = {
    "python_workers",
    "python_workflows",
}

_ACCOUNT_ID_PLACEHOLDER = "{{CLOUDFLARE_ACCOUNT_ID}}"
_D1_DATABASE_NAME_PLACEHOLDER = "{{PULSE_D1_DATABASE_NAME}}"
_D1_DATABASE_ID_PLACEHOLDER = "{{CLOUDFLARE_D1_DATABASE_ID}}"
_VECTORIZE_INDEX_PLACEHOLDER = "{{PULSE_VECTORIZE_INDEX_NAME}}"
_PODCAST_BUCKET_PLACEHOLDER = "{{PULSE_PODCAST_BUCKET_NAME}}"


def _required_template_fragments() -> Tuple[str, ...]:
    compatibility_flags = tuple(f'"{flag}"' for flag in REQUIRED_COMPATIBILITY_FLAGS)

    return (
        f'"name": "{WORKER_NAME}"',
        f'"main": "{WORKER_MAIN}"',
        *compatibility_flags,
        f'"name": "{WORKFLOW_NAME}"',
        f'"binding": "{WORKFLOW_BINDING}"',
        f'"class_name": "{WORKFLOW_CLASS}"',
        f'"binding": "{D1_BINDING}"',
        '"binding": "PULSE_PODCAST_BUCKET"',
        f'"{SCHEDULER_CRON}"',
        _ACCOUNT_ID_PLACEHOLDER,
        _D1_DATABASE_NAME_PLACEHOLDER,
        _D1_DATABASE_ID_PLACEHOLDER,
        _VECTORIZE_INDEX_PLACEHOLDER,
        _PODCAST_BUCKET_PLACEHOLDER,
    )


def validate_wrangler_template(
    template: str,
) -> None:
    missing = [fragment for fragment in _required_template_fragments() if fragment not in template]

    if missing:
        raise RuntimeError(
            "Wrangler template is missing required configuration: " + ", ".join(missing)
        )


def render_wrangler_config(
    *,
    account_id: str,
    d1_database_name: str,
    d1_database_id: str,
    vectorize_index_name: str,
    podcast_bucket_name: str,
) -> str:
    template = WRANGLER_TEMPLATE_PATH.read_text()

    validate_wrangler_template(
        template,
    )

    replacements: Dict[str, str] = {
        _ACCOUNT_ID_PLACEHOLDER: account_id,
        _D1_DATABASE_NAME_PLACEHOLDER: d1_database_name,
        _D1_DATABASE_ID_PLACEHOLDER: d1_database_id,
        _VECTORIZE_INDEX_PLACEHOLDER: vectorize_index_name,
        _PODCAST_BUCKET_PLACEHOLDER: podcast_bucket_name,
    }

    rendered = template

    for placeholder, value in replacements.items():
        rendered = rendered.replace(
            placeholder,
            value,
        )

    unresolved = [placeholder for placeholder in replacements if placeholder in rendered]

    if unresolved:
        raise RuntimeError(
            "Wrangler configuration contains unresolved placeholders: " + ", ".join(unresolved)
        )

    return rendered
