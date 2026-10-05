# Changelog

All notable changes to Pulse will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-04

### Added

- Initial public release of Pulse.
- End-to-end generation of podcast episodes from curated X lists.
- Retrieval and reconstruction of X conversations and thread context.
- Canonicalization and exact deduplication of retrieved signals.
- Semantic embeddings and semantic deduplication with Voyage AI and Cloudflare Vectorize.
- Interest-based signal scoring, filtering, and augmentation.
- Theme extraction and grouping of related signals.
- Multi-stage episode planning, scripting, and metadata generation with Anthropic models.
- Text-to-speech generation with ElevenLabs.
- Podcast audio and RSS publishing through Cloudflare R2.
- Spotify-compatible RSS output.
- LangGraph-based pipeline orchestration.
- Durable cloud execution with Cloudflare Workers and Workflows.
- Checkpointed and resumable pipeline runs using Cloudflare D1.
- Separate local and cloud runtime composition paths.
- Pipeline, show, schedule, run, and operational persistence through Cloudflare D1.
- CLI workflows for initialization, configuration, deployment, scheduling, execution, and run recovery.
- Scheduled pipeline execution through Cloudflare cron triggers.
- Structured run and node logging for pipeline observability.
- No-content completion paths that terminate cleanly without publishing an episode.
- Post-publication signal commits to prevent unpublished content from being consumed after failed runs.
- Local development and end-to-end execution workflows.
- Unit, integration, and end-to-end test coverage.
- Ruff linting, Pyright type checking, and pytest-based testing.
- Documentation for getting started, configuration, deployment, operations, troubleshooting, architecture, development, contributing, and releases.
- Apache 2.0 license.

[Unreleased]: https://github.com/joolaoye/pulse/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/joolaoye/pulse/releases/tag/v0.1.0