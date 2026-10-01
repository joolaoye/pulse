# Architecture

Pulse is a scheduled podcast-generation system that turns a curated source stream into published podcast episodes.

At a high level, Pulse has three architectural layers:

1. a **control plane** that stores application configuration and decides when pipelines should run;
2. an **execution layer** that adapts local and Cloudflare invocations into the same application runtime; and
3. an **episode pipeline** that retrieves, processes, generates, and publishes one logical run.

Both local CLI execution and production Cloudflare execution converge on the same application and pipeline runtime.

---

## System overview

![Pulse system architecture](assets/pulse-system-architecture.svg)

Pulse separates long-lived configuration and scheduling from the execution of individual podcast runs.

At the highest level, the system has three cooperating layers:

- the **control plane** stores shows, pipelines, and schedules and determines when configured pipelines should run;
- the **execution layer** provides local and Cloudflare adapters that converge on the same Pulse application runtime; and
- the **episode pipeline** retrieves source material, processes it into `ProcessedSignal` values, produces an episode, publishes it, and then commits that run's signal history.

The important architectural boundary is that **configuration and scheduling decide what should run and when; the episode pipeline decides how one run executes**.

Cloudflare-specific code remains an adapter around the Pulse application rather than becoming the owner of podcast-generation behavior.

---

## Source to podcast lifecycle

For V1, Pulse retrieves content from a configured X list and turns that source material into a published podcast episode.

The episode path is:

```text
X list
    ↓
source retrieval
    ↓
ingestion + exact deduplication
    ↓
semantic processing
    ↓
relevance scoring / filtering / augmentation
    ↓
signal grouping
    ↓
episode planning
    ↓
script generation
    ↓
episode metadata
    ↓
audio production
    ↓
publication
    ↓
signal-history commit
    ↓
RSS
    ↓
podcast client
```

Retrieval first reconstructs the configured source material.

Ingestion converts source material into Pulse's canonical signal representation and removes signals that the current pipeline has already consumed exactly.

Semantic processing embeds signals and compares them against the pipeline's semantic history so that materially repeated stories can also be excluded.

Post-processing decides which remaining signals are sufficiently relevant to the pipeline's interest profile to carry into generation.

Related signals are then grouped into coherent themes before the generation stages create the episode plan, final script, metadata, and synthesized audio.

Publication writes the episode's durable publication state and public podcast artifacts before the run commits its signal history.

For detailed behavior inside these stages, see:

- [Retrieval](architecture/retrieval.md)
- [Semantic processing](architecture/semantics.md)
- [Generation](architecture/generation.md)
- [Publishing](architecture/publishing.md)

---

## Control plane and episode pipeline

Pulse deliberately separates configuration lifecycle from episode execution.

### Control plane

The control plane owns long-lived application configuration:

```text
PodcastShow
PodcastPipeline
Schedule
```

It is operated primarily through the Pulse CLI and persisted in D1.

The scheduler also belongs to this side of the architecture. A recurring Cloudflare Cron Trigger wakes the Worker scheduler, which finds due pipeline schedules and starts the appropriate Cloudflare Workflow instances.

The scheduler does not contain podcast-generation logic.

Conceptually:

```text
Cron heartbeat
    ↓
find due enabled schedules
    ↓
start one Cloudflare Workflow per due occurrence
    ↓
compare-and-swap each schedule to its next occurrence
    ↓
each Workflow runs the existing Pulse pipeline
```

For the complete scheduling model, including persisted schedules, Cron dispatch, and compare-and-swap advancement, see [Scheduling](architecture/scheduling.md).

### Episode pipeline

The episode pipeline represents one logical Pulse run.

It receives a persisted pipeline identity and resolves the configuration required to execute it:

```text
pipeline_id
    ↓
PodcastPipeline
    ↓
PodcastShow
    ↓
pipeline-specific runtime
    ↓
LangGraph
```

`RunManager` owns the application-level execution use case, while `PodcastPipelineRuntimeFactory` constructs the pipeline-specific services required by that run.

This keeps execution independent of whether the run was initiated manually or by Cloudflare.

---

## Show, Pipeline, and Schedule

Pulse keeps publication identity, generation behavior, and execution timing separate.

| Model | Owns | Does not own |
| --- | --- | --- |
| `PodcastShow` | Podcast identity, public metadata, RSS/publication destination | How an episode is generated or when it runs |
| `PodcastPipeline` | Interests, source configuration, podcast profile, speakers, voices, target duration, enabled state | Public show identity or execution timing |
| `PodcastPipelineSchedule` | When a pipeline should execute | Generation or publication configuration |

The relationship is:

```text
PodcastShow
    publication identity
         ↑
         │ show_id
         │
PodcastPipeline
    generation configuration
         ↑
         │ pipeline_id
         │
PodcastPipelineSchedule
    execution timing
```

Multiple architectural concerns can therefore evolve independently.

Changing a schedule does not require redeploying the Worker.

Changing generation configuration does not redefine the show's RSS identity.

The same show can also remain the publication destination while its generation configuration evolves.

For the complete field-level model, see [Configuration](configuration.md).

---

## Execution adapters

Pulse supports two primary execution adapters.

```text
Pulse CLI
    ↓
RunManager
```

is used for manual execution and development.

Production scheduled execution uses:

```text
Cloudflare Cron
    ↓
Worker scheduler
    ↓
Cloudflare Workflow
    ↓
RunManager
```

After `RunManager`, both paths use the same runtime factory, services, and LangGraph workflow.

This is an intentional architectural rule:

> Adapters decide how Pulse is invoked. They do not implement the Pulse pipeline.

The CLI therefore does not construct LangGraph nodes or perform direct generation orchestration, and the Cloudflare Worker does not contain a second implementation of the episode workflow.

---

## LangGraph

![Pulse LangGraph workflow](assets/pulse-langgraph-architecture.svg)

LangGraph is the **application-level workflow orchestrator** for a single Pulse run.

It owns the ordering, state transitions, and conditional routing between Pulse's major processing stages.

The normal episode-producing path is:

```text
retrieve_sources
→ ingest_signals
→ process_semantics
→ post_process_signals
→ group_signals
→ plan_episode
→ generate_script
→ generate_episode_metadata
→ produce_audio
→ publish_episode
→ commit_signals
→ END
```

Four empty-result exits route to `complete_without_episode`, which goes directly to `END`:

```text
ingest_signals            → no_unseen_signals
process_semantics         → no_semantically_unique_signals
post_process_signals      → no_processed_signals
group_signals             → no_themed_clusters
```

Graph nodes are intentionally thin.

Each node delegates the actual work to an existing Pulse service or aggregate rather than embedding domain behavior into the orchestration layer.

LangGraph also provides the state and checkpoint model that makes a run restartable.

A successful run has one of two business outcomes:

```text
PUBLISHED
NO_CONTENT
```

`NO_CONTENT` is not an execution failure. It means that the pipeline completed successfully but did not find enough sufficiently new and relevant material to produce an episode.

Unexpected execution failures remain failures rather than being represented as another successful workflow outcome.

---

## Cloudflare Workflow

Cloudflare Workflow and LangGraph solve different problems.

```text
Cloudflare Workflow
    durable production execution envelope
            ↓
        RunManager
            ↓
        LangGraph
    Pulse episode orchestration
```

A Cloudflare Workflow instance represents one production invocation of a Pulse pipeline.

It provides the outer Cloudflare execution boundary used by scheduled runs.

It does **not** model retrieval, semantic processing, planning, scripting, or publishing stages individually.

Those stages remain owned by LangGraph and the Pulse application.

This separation prevents the production platform from becoming coupled to the internal editorial pipeline.

---

## Persistence and storage

Pulse uses three Cloudflare persistence systems for different responsibilities.

### Cloudflare D1

D1 is the application's durable relational state.

It stores concerns such as:

```text
PodcastShow configuration
PodcastPipeline configuration
Schedules and scheduled occurrences
Exact signal history
Episode publication records
LangGraph checkpoints
```

D1 is also the production LangGraph checkpoint store.

### Cloudflare Vectorize

Vectorize stores semantic signal history.

Pulse uses embeddings to detect when a new source item is materially similar to content the same pipeline has already consumed.

The index can be shared across pipelines because semantic history is partitioned by `pipeline_id`.

### Cloudflare R2

R2 stores published podcast assets:

```text
episode audio
RSS feeds
```

Show artwork is the public `artwork_url` configured on `PodcastShow`. Pulse references that URL from RSS. It does not upload artwork during publication.

Audio and RSS objects are addressed through the show's `public_base_url`. Podcast clients fetch them without Cloudflare credentials.

For provisioning, bindings, permissions, and public-bucket configuration, see [Deployment](deployment.md).

---

## External providers

Pulse keeps external-provider responsibilities narrow.

| Provider | Role |
| --- | --- |
| X | Source retrieval and conversation/discourse loading |
| Voyage AI | Embeddings used for semantic processing and deduplication |
| Anthropic | Theme extraction, planning, scripting, conversation polish, and episode metadata. Relevance filtering is local scoring in `SignalFilter`, not an Anthropic call. |
| ElevenLabs | Text-to-speech synthesis for the finalized episode script |

Provider integrations sit behind Pulse service boundaries.

LangGraph nodes do not directly contain provider-specific orchestration logic unless the provider is part of the service they invoke.

This keeps provider replacement and service testing separate from graph structure.

---

## Checkpointing and resume

![Pulse retry and resume architecture](assets/pulse-retry-architecture.svg)

Episode generation includes expensive and externally visible operations.

Pulse therefore treats restartability as a core runtime property.

Each logical run has a stable `run_id`. LangGraph uses that run identity as its checkpoint thread identity.

During production execution, graph state is persisted to D1 as the run progresses.

Conceptually:

```text
run stage succeeds
    ↓
state checkpoint
    ↓
next stage
```

If a later stage fails, the same logical run can resume from its persisted state rather than creating a new episode run from scratch.

For example:

```text
script generated
    ↓
audio generated
    ↓
publication fails
    ↓
run stops

resume same run_id
    ↓
restore checkpoint
    ↓
reuse completed work
    ↓
retry publication
```

Resume is therefore different from starting a new run.

A resumed run keeps the same logical run and episode identity.

---

## Publication before signal commit

Signal-history persistence is deliberately ordered after the run reaches a successful business outcome.

On the episode-producing path:

```text
generate episode
    ↓
publish episode
    ↓
commit signal history
```

rather than:

```text
generate episode
    ↓
commit signal history
    ↓
attempt publication
```

This ordering matters.

If signals were marked as consumed before publication and publication then failed, a future fresh run could incorrectly treat those signals as already handled even though no episode was successfully published.

Pulse therefore makes publication the first durable success boundary for an episode-producing run.

Only after publication succeeds does `CommitSignalsNode` update the pipeline's signal history.

A successful `NO_CONTENT` run ends at `complete_without_episode`. That node goes directly to `END`. It does not publish and it does not call `CommitSignalsNode`, so it does not write signal history.

The general invariant is:

> A failed run must not make source material appear successfully consumed by that pipeline.

For publication transactions, idempotency, RSS updates, and commit behavior, see [Publishing](architecture/publishing.md).

---

## Pipeline-scoped signal history

Signal history belongs to a `PodcastPipeline`, not globally to the Pulse installation.

This is important because two pipelines can legitimately interpret the same source material differently.

For example:

```text
Pipeline A
    AI infrastructure interests

Pipeline B
    startup / market interests
```

A source item consumed by Pipeline A must not automatically disappear from Pipeline B.

Exact signal identity is therefore scoped by pipeline:

```text
pipeline_id + source + signal_id
```

Semantic history follows the same model.

Pulse can use a shared Vectorize index, but records carry `pipeline_id` metadata and semantic-history queries are filtered to the current pipeline.

Conceptually:

```text
shared infrastructure
        ↓
   pulse-signals
      Vectorize
        ↓
 ┌───────────────┐
 │ pipeline A    │
 │ pipeline B    │
 │ pipeline C    │
 └───────────────┘
```

This allows infrastructure to be shared without allowing one pipeline's editorial history to suppress another pipeline's source material.

For exact and semantic deduplication behavior, see [Semantic processing](architecture/semantics.md).

---

## Architectural boundaries

Several rules keep the system maintainable:

```text
CLI / Worker
    invocation adapters

Application layer
    setup, configuration, scheduling, execution

LangGraph
    episode-stage orchestration

Services
    Pulse capabilities and domain behavior

Infrastructure
    D1, R2, Vectorize, provider and Cloudflare implementations
```

Dependencies should flow toward stable application and service boundaries rather than allowing adapters to own business logic.

In particular:

- the scheduler decides **when** a pipeline runs;
- `RunManager` decides **which logical run** is being executed;
- `PodcastPipelineRuntimeFactory` resolves **what runtime that pipeline needs**;
- LangGraph decides **which episode stage executes next**;
- services decide **how each capability is performed**;
- infrastructure adapters decide **how external systems are accessed**.

---

## Related architecture documentation

This page intentionally describes only the system-wide architecture.

Subsystem behavior lives in dedicated documents:

- [Retrieval](architecture/retrieval.md) — X retrieval, discourse reconstruction, and source caching.
- [Semantic processing](architecture/semantics.md) — ingestion, exact deduplication, embeddings, semantic history, scoring, and filtering.
- [Generation](architecture/generation.md) — grouping, episode planning, scripting, metadata, and audio production.
- [Publishing](architecture/publishing.md) — audio persistence, publication records, RSS, idempotency, and signal commit.
- [Scheduling](architecture/scheduling.md) — persisted schedules, Cron dispatch, and compare-and-swap advancement.

For other system concerns:

- [Configuration](configuration.md) — Show, Pipeline, Schedule, speakers, voices, and interest profiles.
- [Deployment](deployment.md) — Cloudflare provisioning, permissions, secrets, build, and deployment.
- [Operations](operations.md) — logs, Workflow inspection, schedules, runs, and production checks.