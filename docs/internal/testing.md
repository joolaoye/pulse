# Testing

Pulse tests live under `tests/` and follow the layout in `pyproject.toml`.

```text
tests/
├── unit/
│   ├── application/
│   ├── cli/
│   ├── infrastructure/
│   ├── services/
│   └── types/
├── integration/
└── e2e/
```

Run the default suite from the repository root:

```bash
uv run pytest
```

The default suite does not include live end-to-end tests. `addopts` in `pyproject.toml` selects `-m "not e2e"`. The live command, including the required list and public feed URL, is in [End to end](#end-to-end).

The same offline command is what `.github/workflows/ci.yml` runs, together with Ruff and Pyright.

## Unit

| Path | What it covers |
| --- | --- |
| `tests/unit/application/deployment/` | Wheel build, deployment inputs, preflight, secrets, Worker bundle, and Wrangler rendering |
| `tests/unit/application/setup/` | Installation and resource setup |
| `tests/unit/application/configuration/` | Show and pipeline managers |
| `tests/unit/application/composition/` | Cloudflare R2 binding composition |
| `tests/unit/application/execution/` | `RunManager` |
| `tests/unit/application/runtime/` | Podcast pipeline runtime factory |
| `tests/unit/application/orchestration/` | Retry policy, logging, and individual graph nodes |
| `tests/unit/cli/` | CLI input parsing and `pulse run` |
| `tests/unit/infrastructure/` | R2 audio storage and Vectorize signal persistence |
| `tests/unit/services/retrieval/` | X retrieval, discourse reconstruction, and cache freshness |
| `tests/unit/services/ingestion/` | Source canonicalization, ingest, and exact deduplication against `signals` |
| `tests/unit/services/signals/` | Scoring, filtering, augmentation, semantic deduplication, post-processing, and signal commit |
| `tests/unit/services/grouping/` | Clustering and themed signal groups |
| `tests/unit/services/interests/` | Interest embedding |
| `tests/unit/services/planning/` | Episode, segment, beat, and turn planning |
| `tests/unit/services/scripting/` | Turn generation, script generation, and conversation polish |
| `tests/unit/services/episode_metadata/` | Episode metadata generation |
| `tests/unit/services/audio/` | MP3 assembly and audio production |
| `tests/unit/services/publishing/` | Publication, RSS rendering, and RSS upload |
| `tests/unit/types/` | Show and pipeline validation |
| `tests/unit/test_schedule_manager.py` | Schedule set, due listing, and occurrence advancement |
| `tests/unit/test_schedule_time.py` | Daily occurrence calculation, including timezone changes |
| `tests/unit/test_scheduled_workflow_id.py` | Deterministic scheduled Workflow instance ids |

Deployment behavior is covered by these tests. There is no separate `scripts/` test harness.

## Integration

Integration tests run repository SQL against a local SQLite stand-in of `DatabaseClient`. They do not call Cloudflare D1.

| Path | What it covers |
| --- | --- |
| `tests/integration/test_show_repository.py` | Podcast show persistence |
| `tests/integration/test_pipeline_repository.py` | Podcast pipeline persistence |
| `tests/integration/test_schedule_repository.py` | Schedule persistence, including the compare-and-swap update of `next_run_at` |
| `tests/integration/test_signal_repository.py` | Signal history persistence |
| `tests/integration/test_episode_publication_repository.py` | Episode publication persistence |
| `tests/integration/test_x_discourse_cache_repository.py` | X discourse cache persistence |
| `tests/integration/test_pipeline_graph.py` | LangGraph publish, `NO_CONTENT`, failed publication, and resume against a local SQLite checkpointer |

`test_pipeline_graph.py` drives `PulseGraphBuilder` with fake providers. A published run commits signals. `complete_without_episode` ends without that commit. A failed publication does not commit. Resume continues the same logical run.

## End to end

`tests/e2e/test_pipeline.py` runs one pipeline through `RunManager` against the live X, Voyage, Anthropic, ElevenLabs, and Cloudflare resources in the local environment. It creates a show and pipeline for the list you pass in, publishes an episode, and checks that the public audio and RSS URLs are reachable.

The test is marked `e2e`. `uv run pytest` skips it. `-m e2e` selects it. `-s` leaves the live run output on the console. `--x-list-id` and `--public-podcast-base-url` are required.

From the repository root, with the project environment active:

```bash
python -m pytest tests/e2e/test_pipeline.py \
  -m e2e \
  -s \
  --x-list-id="<x-list-id>" \
  --public-podcast-base-url="https://pub-example.r2.dev"
```

A failed run prints its run id. Resume continues that same local checkpoint instead of starting another episode:

```bash
python -m pytest tests/e2e/test_pipeline.py \
  -m e2e \
  -s \
  --x-list-id="<x-list-id>" \
  --public-podcast-base-url="https://pub-example.r2.dev" \
  --resume-run-id="<RUN_ID>"
```

`--resume-run-id` calls `RunManager.resume` for that run and pipeline. Omit it to start a fresh run.

## What the suite does not cover

The current tree does not include a Worker scheduled-handler test. Cron dispatch, Workflow creation, and the compare-and-swap schedule advance are covered at the `ScheduleManager` and repository layers, not by executing `workers/cloudflare/entrypoint.py`.
