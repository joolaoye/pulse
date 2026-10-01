# Semantic Processing

Pulse's signal-processing path turns retrieved source material into a small set of new, relevant, generation-ready signals.

For V1, that path spans three LangGraph stages:

```text
ingestion
    ↓
semantic processing
    ↓
post-processing
```

Together they answer three different questions:

```text
ingestion
    → Have we already handled this exact source item?

semantic processing
    → Have we already handled this idea?

post-processing
    → Does this signal matter enough to this pipeline to carry forward?
```

The result is a set of `ProcessedSignal` objects that can enter grouping and episode generation.

---

## Overview

![Pulse signal processing architecture](../assets/pulse-signal-processing-architecture.svg)

Conceptually:

```text id="n4a9qv"
Discourse[]
    ↓
canonicalization
    ↓
Signal[]
    ↓
exact deduplication
    ↓
unseen Signal[]
    ↓
Voyage embeddings
    ↓
EmbeddedSignal[]
    ↓
semantic deduplication
    ↓
relevance scoring
    ↓
ScoredSignal[]
    ↓
filtering
    ↓
augmentation
    ↓
ProcessedSignal[]
    ↓
grouping
```

No signal-history persistence occurs inside these processing stages.

The accepted signal set remains in workflow state until a published run reaches `CommitSignalsNode`. That node is the only writer of exact and semantic history. `NO_CONTENT` ends at `complete_without_episode` and does not commit.

---

## Ingestion

`IngestSignalsNode` is the boundary between source-specific retrieval and source-independent signal processing.

Retrieval produces:

```text
Discourse[]
```

Ingestion converts each discourse into Pulse's canonical signal representation.

Conceptually:

```text
X Discourse
    ↓
source canonicalization
    ↓
Signal
```

From this point forward, semantic processing does not need to understand X conversation or timeline response shapes.

This separation matters because future retrieval sources can implement their own source canonicalization while still entering the same downstream pipeline.

---

## Exact deduplication

Before Pulse spends an embedding request on a signal, ingestion checks whether the current pipeline has already consumed that exact source item.

Exact signal history written by a published run is stored in the D1 table `signals`.

`CommitSignalsNode` reaches that table through `SignalCommitter` and `SignalRepository.persist`:

```sql
INSERT OR IGNORE INTO signals (
    pipeline_id,
    signal_id,
    source,
    relevance_score
)
```

`Ingestor` calls `ExactDeduplicator.exists`, which reads that same table:

```sql
SELECT 1
FROM signals
WHERE pipeline_id = ?
AND source = ?
AND signal_id = ?
LIMIT 1
```

`migrations/d1/0004_create_signals.sql` creates `signals`. A later fresh run observes a committed row through this query and drops that source item before embedding.

Identity on both statements is pipeline-scoped:

```text
pipeline_id
+
source
+
signal_id
```

This means that:

```text
Pipeline A consumes signal X
```

does not imply:

```text
Pipeline B has consumed signal X
```

even when both pipelines share the same Pulse installation.

Exact deduplication therefore answers:

> Has this specific source item already been successfully handled by this pipeline?

Signals already present in exact history are removed before semantic processing.

The survivors become the workflow's `unseen_signals`.

---

## Why exact and semantic deduplication are separate

Exact identity catches repeated source objects.

It does not catch different posts describing the same underlying event.

For example:

```text
Post A:
Company X launches a new inference platform.

Post B:
Company X releases infrastructure for serving models in production.
```

These may have different source IDs while representing substantially the same story.

Pulse therefore performs two distinct checks:

```text
exact deduplication
    source identity

semantic deduplication
    meaning / story similarity
```

Both are required.

---

## Signal embeddings

Signals that survive exact deduplication are embedded by `SignalEmbedder`.

The current V1 provider is Voyage AI using `voyage-4`.

Signal embeddings are 1024-dimensional vectors.

Conceptually:

```text
Signal
    ↓
canonical embedding text
    ↓
Voyage AI
    ↓
1024-dimensional embedding
    ↓
EmbeddedSignal
```

An embedded signal carries at least:

```text
signal_id
embedding
embedding_version
```

The embedding version is retained so stored semantic history remains interpretable if the embedding implementation changes later.

Voyage is responsible only for producing vectors.

It does not decide whether a signal is a duplicate, relevant, or suitable for generation.

---

## `SemanticProcessor`

`ProcessSemanticsNode` delegates the semantic stage to `SemanticProcessor`.

The service coordinates:

```text
SignalEmbedder
    ↓
SemanticDeduplicator
```

and returns the signals that remain semantically unique.

The node stores the surviving embeddings by stable signal identity:

```text
embedded_signals_by_id
```

Later stages join models by `signal_id`, not by list position.

That is an important workflow invariant because scoring, filtering,
grouping, and final signal commit all refer back to the same logical signal.

---

## Vectorize

Cloudflare Vectorize is Pulse's durable semantic-history store.

The shared index contains embeddings for signals that previous successful runs have consumed.

Conceptually:

```text
pulse-signals
    ├── pipeline A history
    ├── pipeline B history
    └── pipeline C history
```

The infrastructure is shared, but semantic history is not global.

Each persisted vector carries `pipeline_id` metadata, and semantic-history queries are filtered to the current pipeline.

`pulse init` prepares the Vectorize index and the metadata index required for `pipeline_id` filtering.

This gives Pulse:

```text
shared Vectorize infrastructure
+
isolated editorial history
```

without requiring one physical Vectorize index per podcast pipeline.

---

## Semantic deduplication

For each new embedded signal, `SemanticDeduplicator` queries the configured Vectorize index for nearby vectors belonging to the same `pipeline_id`.

Conceptually:

```text
new signal embedding
    ↓
Vectorize nearest-neighbor query
    ↓
pipeline_id filter
    ↓
similarity comparison
    ↓
configured duplicate threshold
```

If an existing signal exceeds the configured similarity threshold, the new signal is treated as semantically redundant.

Otherwise, it remains eligible for post-processing.

The default similarity threshold is `0.85` and the default Vectorize query depth is `top_k=1`. Both are constructor arguments on `SemanticDeduplicator`, not workflow state.

---

## Same-run semantic deduplication

Durable Vectorize history only contains signals committed by earlier successful runs.

That creates another case that semantic processing must handle:

```text
signal A
    new this run

signal B
    also new this run
    but semantically equivalent to A
```

Neither is in Vectorize yet.

Pulse therefore also compares semantic survivors against embeddings already accepted during the current run.

Conceptually:

```text
candidate
    ↓
historical comparison
    → Vectorize

candidate
    ↓
current-run comparison
    → in-memory / checkpointed embeddings
```

Current-run comparison uses cosine similarity and the same semantic similarity threshold as historical deduplication.

The current-run vectors remain workflow state; they are not written to Vectorize during semantic processing.

This preserves publication-before-commit while still preventing duplicate stories from surviving the same episode run.

---

## Interest profile

A `PodcastPipeline` carries an interest profile written in Markdown.

For example:

```markdown
# AI Infrastructure

Interested in inference systems, model serving, accelerators,
vector databases, and distributed AI infrastructure.

# Developer Tools

Interested in developer productivity, coding agents,
infrastructure tooling, and software engineering workflows.
```

The interest profile represents what a particular pipeline considers relevant.

It is therefore part of generation configuration rather than global Pulse configuration.

Two pipelines can retrieve the same X material and produce different selected signal sets because they use different interest profiles.

---

## Interest embeddings

When a pipeline runtime is constructed, Pulse parses the interest profile and embeds its semantic interest units using the same Voyage embedding provider used for signals.

Conceptually:

```text
interest profile Markdown
    ↓
InterestParser
    ↓
Interest[]
    ↓
InterestEmbedder
    ↓
EmbeddedInterest[]
```

Each interest unit is embedded independently rather than reducing the complete profile to one vector.

This lets a signal match strongly against one part of the profile without requiring the entire interest document to be semantically similar.

Interest embeddings are pipeline-runtime context.

They are used for relevance scoring; they are separate from the historical signal vectors stored in Vectorize.

---

## Relevance scoring

Signals that survive semantic deduplication enter `PostProcessSignalsNode`.

`PostProcessor` first uses `SignalScorer` to compare each signal embedding with the pipeline's embedded interests.

Conceptually:

```text
EmbeddedSignal
        +
EmbeddedInterest[]
        ↓
cosine similarities
        ↓
strongest interest matches
        ↓
relevance score
```

The scorer considers the strongest interest matches rather than treating the interest profile as one monolithic vector.

The current scoring configuration combines the strongest and next-strongest interest matches to produce the final relevance score.

`SignalScorer` combines the strongest match at weight `0.7` with the next match at weight `0.3`. Downstream stages consume that relevance score on `ProcessedSignal` rather than recomputing it.

This keeps the distinction clear:

```text
semantic deduplication
    → Is this story new?

relevance scoring
    → Do we care about this story?
```

---

## Filtering

`SignalFilter` applies the pipeline's relevance cutoff after scoring.

The current default threshold is:

```text
0.50
```

Conceptually:

```text
relevance_score >= threshold
    → keep

relevance_score < threshold
    → discard
```

Filtering occurs before expensive source augmentation.

This is deliberate.

Pulse should not spend additional X requests collecting community context for signals that are already too weakly related to the interest profile.

The output of filtering is therefore the small set of signals worth enriching and potentially carrying into generation.

---

## Post-processing and augmentation

Signals that survive filtering are augmented with additional source context.

For X, `XSignalAugmenter` can load community-reply context for the selected signal.

The V1 reply-fetch ceiling is:

```text
10 replies
```

The ordering is:

```text
score
    ↓
filter
    ↓
augment
```

rather than:

```text
augment everything
    ↓
score
    ↓
discard most of it
```

This keeps external API work bounded and concentrates richer context on signals that have already passed the semantic and relevance gates.

Augmentation does not change whether a source item is new.

It enriches the context available to later editorial stages.

---

## `ProcessedSignal`

The post-processing stage produces the accepted signal set represented in workflow state as:

```text
processed_signals_by_id
```

This set is the semantic boundary between selection and generation.

A processed signal has survived:

```text
exact deduplication
semantic deduplication
relevance scoring
filtering
augmentation
```

These are the signals Pulse considers successfully selected for the current pipeline run.

---


## What enters grouping

Only accepted `ProcessedSignal` objects enter the grouping stage.

Conceptually:

```text
ProcessedSignal[]
    ↓
GroupSignalsNode
```

Signals rejected by:

```text
exact deduplication
semantic deduplication
relevance filtering
```

never reach episode planning.

This is why a successful Pulse run may legitimately terminate before generation.

For example:

```text
retrieved material exists
    ↓
all exact duplicates
    ↓
NO_CONTENT
```

or:

```text
unseen material exists
    ↓
all semantically redundant
    ↓
NO_CONTENT
```

or:

```text
semantically new material exists
    ↓
nothing meets relevance threshold
    ↓
NO_CONTENT
```

These are successful editorial outcomes, not processing failures.

---

## Signal-history persistence

Signal processing deliberately does **not** mark signals as consumed while the episode is still in progress.

The workflow retains the required forms in checkpointed state:

```text
unseen_signals
embedded_signals_by_id
processed_signals_by_id
```

The accepted set is committed only after the run reaches a successful business path.

For an episode-producing run:

```text
post-process signals
    ↓
generate episode
    ↓
publish episode
    ↓
CommitSignalsNode
```

For a successful no-content run:

```text
processing / grouping
    ↓
CompleteWithoutEpisodeNode
    ↓
END
```

`NO_CONTENT` does not write D1 or Vectorize signal history.

A failure before `CommitSignalsNode` completes does not update durable signal history.

This is the central persistence invariant:

> A failed run must not make source material appear successfully consumed.

---

## `CommitSignalsNode`

`CommitSignalsNode` receives the checkpointed signal state required to persist the run's accepted signal history:

```text
unseen_signals
embedded_signals_by_id
processed_signals_by_id
```

Stable `signal_id` values are used to join the representations.

The processed set determines which successfully accepted signals are eligible for commitment.

Commit performs two complementary writes:

```text
D1
    exact signal history

Vectorize
    semantic signal history
```

The writes are pipeline-scoped.

Conceptually:

```text
processed signal
    ├── source identity
    │       ↓
    │      D1
    │
    └── embedding
            ↓
        Vectorize
```

The persistence operations are designed to be idempotent so that resuming a run around the commit boundary does not create duplicate history.

---

## Why persistence happens last

Consider the alternative:

```text
select signals
    ↓
persist history
    ↓
generate episode
    ↓
publication fails
```

A completely new run could then see those signals as already consumed even though no episode was successfully published.

Pulse instead uses:

```text
select
    ↓
checkpoint
    ↓
generate
    ↓
publish episode
    ↓
commit history
```

Checkpointing protects expensive intermediate work.

Signal history represents successful consumption.

Those are related but intentionally different concepts.

---

## Pipeline-scoped semantics

Every stateful deduplication decision belongs to a `PodcastPipeline`.

Exact history:

```text
pipeline_id + source + signal_id
```

Semantic history:

```text
Vectorize vector
    metadata.pipeline_id
```

Interest relevance:

```text
PodcastPipeline.interest_profile
```

The resulting architecture is:

```text
same source material
        ↓
 ┌──────────────┬──────────────┐
 │ Pipeline A   │ Pipeline B   │
 │ interests A  │ interests B  │
 │ history A    │ history B    │
 └──────────────┴──────────────┘
        ↓               ↓
different selection decisions
```

A pipeline's editorial history therefore cannot suppress another pipeline's material.

---

## Failure and resume behavior

Ingestion, embedding, semantic deduplication, and post-processing are checkpointed LangGraph stages.

A provider or infrastructure failure surfaces as a workflow failure rather than silently dropping affected signals.

For example:

```text
ingestion succeeds
    ↓
checkpoint
    ↓
Voyage request fails
    ↓
run fails
```

Resuming the same logical run restores the previous checkpoint and retries from the appropriate workflow boundary.

Because durable signal history has not yet been committed, the failed run has not falsely consumed its selected source material.

---

## Architectural boundaries

This subsystem owns:

```text
source canonicalization
exact deduplication
signal embeddings
semantic deduplication
interest embeddings
relevance scoring
filtering
source augmentation
commit-ready signal state
```

It does not own:

```text
source discovery / conversation reconstruction
topic clustering
episode planning
script generation
audio generation
publication
```

The complete boundary is:

```text
retrieval
    ↓
Discourse[]
    ↓
signal processing
    ↓
ProcessedSignal[]
    ↓
grouping / generation
```

---

## Related documentation

- [System architecture](../architecture.md) — overall Pulse execution and persistence boundaries.
- [Retrieval](retrieval.md) — X list discovery, discourse reconstruction, and retrieval caching.
- [Generation](generation.md) — grouping, planning, scripting, metadata, and audio.
- [Publishing](publishing.md) — publication, RSS, and successful signal-history commit.
- [Configuration](../configuration.md) — pipeline interest profiles and generation configuration.
- [Deployment](../deployment.md) — Voyage credentials and Vectorize provisioning.