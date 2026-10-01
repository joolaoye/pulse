# Pulse Documentation

Pulse documentation is organized by audience: using Pulse, understanding its architecture, and contributing to the project.

## Using Pulse

- [Getting started](getting-started.md) — install Pulse, configure providers, create a show and pipeline, schedule it, and deploy.
- [Configuration](configuration.md) — configure shows, pipelines, schedules, interests, speakers, voices, and publishing.
- [Deployment](deployment.md) — deploy Pulse to Cloudflare and configure its runtime resources and secrets.
- [Operations](operations.md) — run and inspect deployed Pulse instances, schedules, workflows, logs, and published feeds.
- [Troubleshooting](troubleshooting.md) — diagnose common setup, deployment, runtime, RSS, and podcast-client issues.

## Architecture

- [Architecture overview](architecture.md) — system boundaries, execution model, storage, providers, and the end-to-end podcast pipeline.
- [Retrieval](architecture/retrieval.md) — X retrieval, conversation reconstruction, caching, and source normalization.
- [Semantic processing](architecture/semantics.md) — embeddings, exact and semantic deduplication, relevance scoring, and filtering.
- [Generation](architecture/generation.md) — grouping, planning, scripting, metadata generation, and audio production.
- [Publishing](architecture/publishing.md) — audio persistence, publication records, RSS generation, signal commit, and podcast delivery.
- [Scheduling](architecture/scheduling.md) — persisted schedules, the Cloudflare scheduler heartbeat, workflow dispatch, and retry boundaries.

## Contributing

- [Contributing](../CONTRIBUTING.md) — contribution workflow and pull-request expectations.
- [Development](internal/development.md) — local development setup, repository structure, Worker constraints, and project conventions.
- [Testing](internal/testing.md) — the current unit, integration, and end-to-end layout.
- [Release process](internal/release.md) — maintainer release and verification workflow.

> `docs/internal/` contains contributor and maintainer documentation. It is public documentation, but it is not required for normal Pulse usage.
