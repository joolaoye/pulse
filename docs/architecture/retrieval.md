# Retrieval

Pulse V1 uses a configured X list as its source boundary.

Retrieval discovers recent list activity, resolves that activity into conversation-level context, reconstructs a canonical `Discourse`, and hands those discourses to ingestion.

The retrieval stage is intentionally source-specific:

```text
X API
    ↓
X retrieval
    ↓
Discourse[]
    ↓
ingestion
```

It does not score relevance, perform semantic deduplication, or decide which material should appear in an episode.

Those responsibilities belong to later pipeline stages.

---

## Overview

![Pulse retrieval architecture](../assets/pulse-retrieval-architecture.svg)

The V1 retrieval path is:

```text
configured X list
    ↓
list timeline discovery
    ↓
deduplicate by conversation_id
    ↓
resolve each conversation
    ↓
D1 discourse cache
    ├── fresh hit → reuse cached discourse
    ├── stale hit → incrementally refresh
    └── miss      → hydrate conversation
    ↓
reconstruct canonical Discourse
    ↓
RetrieveSourcesNode
    ↓
WorkflowState.discourses
    ↓
IngestSignalsNode
```

The X list provides **discovery breadth**.

Conversation loading and discourse reconstruction provide the **context required to understand each discovered item**.

---

## X list as the source boundary

Each `PodcastPipeline` identifies the X list it follows through its configured `x_list_id`.

For V1:

```text
PodcastPipeline.x_list_id
    ↓
X list timeline
    ↓
XRetriever
```

The list defines the set of accounts whose recent activity Pulse considers for that pipeline.

Pulse does not currently use the user's home timeline, keyword search, trending topics, or a general-purpose source crawler as part of the V1 retrieval path.

The retrieval abstraction nevertheless stops at the canonical `Discourse` boundary. Downstream stages should not depend on X API response shapes.

Conceptually:

```text
X transport models
    ↓
retrieval + reconstruction
    ↓
Discourse
```

That boundary allows future source implementations to be introduced without making X transport objects part of the rest of the podcast pipeline.

---

## Timeline discovery

Retrieval begins with the configured list timeline.

The timeline request is a **discovery operation**, not the final content representation.

Its purpose is to identify recent conversations that may be relevant to the current run.

The V1 discovery ceiling is:

| Operation | V1 maximum |
| --- | ---: |
| List timeline discovery | 50 |
| Conversation hydration / refresh | 25 |
| Reply fetch for later augmentation | 10 |

The list timeline currently uses a maximum of 50 items per retrieval pass.

Increasing the conversation or reply limits does not increase discovery breadth. They control how deeply Pulse may expand an already discovered conversation.

This distinction is intentional:

```text
timeline limit
    = how many candidates Pulse discovers

conversation limit
    = how much source context Pulse may hydrate

reply limit
    = how much later community context may be fetched
```

The current V1 configuration favors bounded retrieval rather than attempting to exhaustively paginate an X list.

---

## Conversation identity

Timeline entries are normalized around their X `conversation_id`.

Several timeline posts may belong to the same conversation, so retrieval does not independently hydrate every discovered tweet.

Instead:

```text
timeline tweets
    ↓
extract conversation_id
    ↓
deduplicate conversation IDs
    ↓
one discourse resolution per conversation
```

`conversation_id` is therefore the stable cache and retrieval identity for X discourse.

This avoids repeatedly loading the same thread when multiple posts from that thread appear in the list timeline.

---

## Conversation loading

A timeline entry alone may not contain enough context to understand what is being discussed.

`XRetriever` resolves the surrounding conversation before returning material to the rest of Pulse.

The retrieval subsystem is composed around:

```text
XRetriever
    ↓
conversation loading
    ↓
DiscourseReconstructor
```

Conversation loading gathers the X objects required to reconstruct the discovered item, including the root post and relevant conversation or referenced-post context.

The resulting transport context is temporary.

Downstream stages consume `Discourse`, not the raw timeline or conversation responses.

---

## Discourse reconstruction

`DiscourseReconstructor` converts X retrieval context into Pulse's canonical X representation.

The primary V1 discourse forms are:

```text
STANDALONE
THREAD
QUOTE
```

### Standalone discourse

A post with no self-thread continuation or quoted-post relationship is represented as a standalone discourse.

Conceptually:

```text
Discourse
    discourse_type = STANDALONE
    root_tweet
    tweets = [root_tweet]
```

### Thread discourse

A self-thread is reconstructed from posts authored by the root author that continue the root conversation.

Thread posts are ordered chronologically before the discourse is returned.

Conceptually:

```text
root post
    ↓
same-author continuation
    ↓
same-author continuation
    ↓
ordered thread
```

Replies from unrelated authors are not treated as authored thread continuation.

### Quote discourse

When the discovered post quotes another post, Pulse preserves that relationship rather than flattening the two posts into unrelated inputs.

Conceptually:

```text
quoting post
    ↓
referenced post
```

The referenced post remains explicit in the canonical discourse so later processing can distinguish the author's commentary from the material being quoted.

---

## Canonical `Discourse`

`Discourse` is the durable boundary between X retrieval and the rest of the Pulse pipeline.

Conceptually it carries:

```text
Discourse
├── discourse_type
├── root_tweet
├── tweets[]
├── referenced_tweet?
└── root_author_username
```

The exact X transport response used to produce those fields is not part of the downstream contract.

This distinction is important:

```text
TimelineResponse
Includes
X API pagination / search responses
        ↓
retrieval implementation detail

Discourse
        ↓
Pulse workflow contract
```

`root_author_username` is preserved with the discourse so later stages can attribute the source without needing another user lookup.

---

## Source context and replies

Pulse distinguishes **source reconstruction** from **community augmentation**.

Initial retrieval is responsible for reconstructing enough context to understand the discovered source:

```text
root post
self-thread context
quoted-post context
```

It does not need to exhaustively fetch and rank community replies for every timeline candidate.

Community-reply enrichment happens later, after earlier processing has reduced the candidate set.

Conceptually:

```text
initial retrieval
    ↓
canonical Discourse
    ↓
ingestion
    ↓
semantic processing
    ↓
scoring / filtering
    ↓
surviving signals
    ↓
X reply augmentation
```

This prevents Pulse from spending X API requests collecting expensive reply context for material that will later be discarded.

The V1 reply-fetch ceiling is 10 results for that later augmentation path.

Retrieval and augmentation may share X infrastructure, but they serve different purposes:

```text
retrieval
    → understand the source

augmentation
    → enrich a surviving signal with community context
```

---

## Discourse cache

Conversation reconstruction can require several X API requests and the same conversation may appear across multiple Pulse runs.

Pulse therefore maintains a durable X discourse cache in D1.

The cache is keyed by:

```text
conversation_id
```

The current persisted shape is:

```text
x_discourse_cache
├── conversation_id
├── discourse_json
├── latest_post_id
└── refreshed_at
```

`discourse_json` contains the reconstructed canonical discourse rather than the original X transport response.

The cache is **source-level infrastructure**, not pipeline signal history.

That distinction is important.

A reconstructed X conversation can safely be reused across pipelines:

```text
shared X discourse cache
```

while exact and semantic consumption history remains scoped independently to each `PodcastPipeline`.

---

## Freshness and revalidation

The V1 discourse cache uses a **24-hour freshness window**.

It does not use a destructive expiration TTL.

Conceptually:

```text
cache lookup
    ↓
age < 24 hours?
    ├── yes → return cached Discourse
    └── no  → revalidate conversation
```

A fresh cache hit avoids loading the conversation from X again.

A stale cache entry is not discarded. Pulse incrementally checks whether the conversation has changed.

This is closer to revalidation than expiration:

```text
fresh
    → reuse

stale
    → refresh

missing
    → fully hydrate
```

---

## Incremental conversation refresh

Each cache entry stores `latest_post_id`.

When a cached discourse becomes stale, Pulse can request only conversation activity newer than that post:

```text
conversation_id
+
since_id = latest_post_id
```

If new posts are returned:

```text
cached discourse
    +
new conversation posts
    ↓
merge
    ↓
reconstruct Discourse
    ↓
update cache
```

If no new posts are returned, Pulse can continue using the existing discourse.

In either case, a successful revalidation updates `refreshed_at`, so that the conversation is not checked again until the next freshness window.

`latest_post_id` represents the newest post belonging to the cached conversation.

A quoted post from another conversation must not become the refresh cursor merely because it is included in the discourse.

---

## Preserving cached context

Incremental X responses do not necessarily repeat every piece of metadata returned during the original hydration.

Refreshing a discourse must therefore preserve canonical information that remains valid but is absent from the incremental response.

For example, the cached `root_author_username` is retained when an incremental refresh does not include the corresponding user object.

The refresh operation is conceptually:

```text
existing canonical discourse
       +
incremental X response
       ↓
merge source context
       ↓
reconstruct canonical discourse
```

rather than:

```text
incremental response
       ↓
replace everything
```

This lets Pulse reduce source requests without degrading the canonical representation over time.

---

## Cache behavior across runs

The cache is intentionally independent of editorial configuration.

Changing:

```text
interest profile
podcast profile
speakers
episode duration
```

does not invalidate an X discourse cache entry.

Those values influence downstream processing, not what the X conversation itself contains.

Therefore:

```text
X retrieval / discourse cache
    source truth

pipeline signal history
    editorial consumption history
```

are separate persistence concerns.

Pulse can reuse the first while recomputing the second for each pipeline.

---

## Failure behavior

Retrieval operates against an external API, so transport, authentication, rate-limit, and malformed-response failures are possible.

Pulse does not treat an incomplete or failed retrieval as a valid reconstructed discourse.

Contract or reconstruction failures should surface rather than silently manufacturing partial source material.

The V1 retrieval path also does not define a separate stale-on-error or skip-failed-conversation success mode.

Conceptually:

```text
X request / reconstruction succeeds
    ↓
return Discourse

X request / reconstruction fails
    ↓
retrieval node fails
    ↓
workflow failure / resume path
```

The failure remains part of the logical Pulse run.

When that run is resumed, already persisted discourse-cache entries can still prevent successfully reconstructed conversations from requiring full hydration again.

Retry and restartability therefore remain orchestration concerns rather than being implemented as unbounded loops inside `XRetriever`.

---

## `RetrieveSourcesNode`

Retrieval enters the LangGraph episode workflow through `RetrieveSourcesNode`.

Its responsibility is deliberately small:

```text
pipeline x_list_id
    ↓
XRetriever.retrieve(...)
    ↓
List[Discourse]
    ↓
WorkflowState.discourses
```

The node does not perform:

```text
exact signal-history deduplication
semantic deduplication
interest scoring
filtering
augmentation
```

Those operations belong to later stages.

This preserves the architectural boundary:

> Retrieval answers **what source material exists and what context does it contain?**

It does not answer:

> **Should this pipeline use it?**

---

## What enters ingestion

The retrieval output passed to `IngestSignalsNode` is:

```text
List[Discourse]
```

stored in workflow state as:

```text
discourses
```

Ingestion is the first stage that converts retrieved source material into Pulse's source-independent signal model.

Conceptually:

```text
Discourse[]
    ↓
IngestSignalsNode
    ↓
canonical Signal[]
    ↓
pipeline-scoped exact deduplication
```

This is the boundary between:

```text
source-specific retrieval
```

and:

```text
source-independent signal processing
```

Retrieval therefore does not produce `ProcessedSignal`, embedded signals, scored signals, or episode-generation inputs.

---

## Architectural boundaries

The retrieval subsystem owns:

```text
X list discovery
X transport access
conversation hydration
discourse caching
incremental conversation refresh
X-specific reconstruction
canonical Discourse output
```

It does not own:

```text
pipeline signal history
semantic history
interest scoring
filtering decisions
topic grouping
episode generation
publication
```

The main ownership chain is:

```text
X API
    ↓
retrieval
    ↓
Discourse
    ↓
ingestion
    ↓
Signal
    ↓
semantic / post-processing
```

Keeping this boundary explicit prevents X transport behavior from leaking into the rest of Pulse.

---

## Related documentation

- [System architecture](../architecture.md) — top-level runtime and application boundaries.
- [Semantic processing](semantics.md) — ingestion, exact deduplication, embeddings, semantic deduplication, scoring, and filtering.
- [Generation](generation.md) — grouping through final audio generation.
- [Publishing](publishing.md) — publication, RSS, and signal-history commit.
- [Configuration](../configuration.md) — pipeline source configuration and `x_list_id`.
- [Operations](../operations.md) — inspecting deployed runs and retrieval failures.