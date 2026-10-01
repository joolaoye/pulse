# Publishing

Pulse's publishing path turns a generated episode into durable podcast state that standard podcast clients can consume.

By the time publishing begins, Pulse has already produced:

```text
EpisodeMetadata
stored episode audio in R2
```

Publishing is responsible for registering the episode, rebuilding the show's RSS feed, and making the resulting feed and media URLs available to podcast clients.

For an episode-producing run, publication also establishes the success boundary that must be crossed before Pulse commits the run's signal history.

---

## Overview

![Pulse publishing architecture](../assets/pulse-publishing-architecture.svg)

Conceptually:

```text
EpisodeMetadata
        +
stored_episode_audio
        +
PodcastShow
        +
episode identity
        ↓
PublishEpisodeNode
        ↓
PodcastPublisher
        ├── persist episode publication → D1
        │
        ├── load show publication catalogue
        │
        ├── render RSS
        │
        └── publish RSS → R2
        ↓
PublicationResult
        ↓
CommitSignalsNode
        ├── exact history → D1
        └── semantic history → Vectorize
```

The audio object itself is persisted before this stage.

That distinction is important:

```text
ProduceAudioNode
    → synthesizes and assembles audio
    → stores audio in R2
    → records stored audio metadata in workflow state

PublishEpisodeNode
    → publishes episode metadata
    → regenerates the RSS feed
    → exposes the stored audio through the feed
```

An uploaded audio object alone does not mean that an episode has been successfully published.

---

## Publication flow

The episode-producing end of the LangGraph workflow is:

```text
GenerateEpisodeMetadataNode
    ↓
ProduceAudioNode
    ↓
PublishEpisodeNode
    ↓
CommitSignalsNode
```

`PublishEpisodeNode` receives the durable episode identity and the completed generation outputs required for publication.

At this point the workflow already knows:

```text
episode_id
published_at
PodcastShow
EpisodeMetadata
stored_episode_audio
```

The stored audio reference includes the object key needed to locate the episode audio in R2.

`PublishEpisodeNode` delegates the publication operation to `PodcastPublisher`.

The resulting `PublicationResult` exposes the published episode identity and public locations, including:

```text
show_id
episode_id
audio_url
feed_url
```

The workflow stores that result as:

```text
publication_result
```

Successful publication then allows the graph to proceed to signal-history commit.

---

## R2 object structure

Pulse uses stable, show-scoped object keys for its public podcast artifacts.

The V1 layout is:

```text
shows/
└── <show-id>/
    ├── rss.xml
    └── episodes/
        └── <episode-id>/
            └── audio.mp3
```

For example:

```text
shows/pulse-test/rss.xml

shows/pulse-test/
    episodes/
        0d2e9df5-3b17-4872-9ec6-4fa2c0a7bcc0/
            audio.mp3
```

The corresponding public URLs are not stored as independent object identities.

They are derived from the show's public origin:

```text
PodcastShow.public_base_url
        +
R2 object key
        ↓
public URL
```

This keeps internal storage identity separate from the hostname through which listeners access the files.

---

## Audio persistence

Audio upload belongs to audio production rather than `PodcastPublisher`.

The end of the audio-generation path is:

```text
AudioAssembler
    ↓
EpisodeAudio
    ↓
AudioRepository
    ↓
R2
    ↓
stored episode audio reference
```

The stored audio state carries information such as:

```text
object_key
output_format
duration_seconds
size_bytes
turn_timings
```

The workflow stores this result before entering publication.

For V1, the stable episode audio object key follows:

```text
shows/<show-id>/episodes/<episode-id>/audio.mp3
```

Because the object key contains the stable episode identity, resuming the same logical run continues to refer to the same episode artifact.

Publishing therefore does not need to synthesize or upload the audio again merely to regenerate the RSS feed.

---

## `PodcastShow` and public URLs

`PodcastShow` owns the podcast's publication identity and public metadata.

Two fields are especially important to publication:

```text
public_base_url
feed_object_key
```

`public_base_url` is the public origin through which podcast clients access Pulse artifacts.

For example:

```text
https://podcasts.example.com
```

`feed_object_key` identifies the RSS feed inside object storage:

```text
shows/pulse-test/rss.xml
```

Together they produce:

```text
https://podcasts.example.com/shows/pulse-test/rss.xml
```

The same rule applies to audio.

Given:

```text
public_base_url:
https://podcasts.example.com

audio object key:
shows/pulse-test/episodes/<episode-id>/audio.mp3
```

the enclosure URL becomes:

```text
https://podcasts.example.com/
    shows/pulse-test/
    episodes/<episode-id>/
    audio.mp3
```

Conceptually:

```text
public URL =
public_base_url.rstrip("/")
+
"/"
+
object_key.lstrip("/")
```

`public_base_url` therefore represents the client-facing origin, not the internal R2 bucket identity.

A deployment can use an R2-managed public development domain or a custom public domain. Production deployments should use a stable public domain because podcast clients persist and revisit feed and enclosure URLs.

---

## Publication records in D1

R2 contains the public files.

D1 contains the durable publication catalogue from which those files are described.

Each published episode has a D1 publication record associated with its show and stable episode identity.

That record preserves the information required to represent the episode in the feed, including its editorial metadata and stored audio reference.

Conceptually:

```text
episode_id
show_id
publication metadata
GUID
publication timestamp
audio object key
audio size
audio duration
audio content type
```

The publication catalogue is authoritative for which episodes belong in a show's RSS feed.

This creates a deliberate split:

```text
D1
    → what has been published

R2
    → the public media and feed artifacts
```

The RSS file itself is therefore a rendered projection of durable application state rather than the only record of published episodes.

---

## RSS regeneration

Pulse does not append XML directly to an existing feed.

Instead, publication rebuilds the feed from durable show and episode state.

Conceptually:

```text
PodcastShow
        +
D1 episode publications for the show
        ↓
RssFeedRenderer
        ↓
complete RSS document
        ↓
RssFeedPublisher
        ↓
PodcastShow.feed_object_key in R2
```

This makes the feed reproducible.

If the RSS object needs to be rewritten, Pulse can reconstruct it from:

```text
PodcastShow
+
persisted episode publication records
```

rather than depending on the previous RSS object's contents.

The resulting feed is an RSS 2.0 document with podcast metadata and one `<item>` for each published episode.

A typical item contains:

```xml
<item>
    <title>...</title>
    <description>...</description>
    <guid isPermaLink="false">
        urn:pulse:<show-id>:<episode-id>
    </guid>
    <pubDate>...</pubDate>
    <enclosure
        url="https://.../audio.mp3"
        length="..."
        type="audio/mpeg"
    />
    <itunes:duration>...</itunes:duration>
</item>
```

The enclosure points to the exact public URL of the already-stored episode audio.

---

## Episode GUIDs

Podcast clients require a stable identifier for each episode.

Pulse derives that identity from the show and episode:

```text
urn:pulse:<show-id>:<episode-id>
```

For example:

```text
urn:pulse:pulse-test:
0d2e9df5-3b17-4872-9ec6-4fa2c0a7bcc0
```

In RSS, the GUID is emitted as a non-permalink identifier:

```xml
<guid isPermaLink="false">
    urn:pulse:pulse-test:<episode-id>
</guid>
```

The GUID is not the audio URL.

Those identities serve different purposes:

```text
GUID
    → stable podcast episode identity

audio URL
    → location of the episode media
```

Keeping the GUID independent of the public hostname means the episode's logical identity is not defined by where its audio happens to be served.

The stable `episode_id` also matters for restartability.

Resuming the same Pulse run retains the same episode identity, which means publication retains the same GUID rather than creating a second podcast episode.

---

## Idempotent publication

Publication can be retried.

It must therefore be safe for the same logical episode identity to pass through the publication path again.

Conceptually:

```text
same show_id
+
same episode_id
        ↓
same logical publication
```

A replay must not intentionally produce:

```text
duplicate D1 publication rows
duplicate RSS items
different episode GUIDs
```

Stable episode identity, stable R2 object keys, and deterministic GUID construction make this possible.

This property is particularly important because publication contains external side effects that LangGraph cannot roll back automatically.

---

## Artwork

`PodcastShow.artwork_url` is part of the show's public podcast metadata.

The RSS renderer includes that configured URL as the show's artwork reference.

For V1, Pulse does **not** own artwork upload as part of the episode publication path.

The configured `artwork_url` must already point to a publicly reachable image before the feed is submitted to a podcast directory.

This means:

```text
episode audio
    → Pulse stores and publishes

RSS feed
    → Pulse renders and publishes

show artwork
    → configured public URL
```

The artwork may be hosted on the same public origin as the feed, but that is a deployment choice rather than a requirement of the publishing service.

The important contract is that podcast clients must be able to fetch the configured artwork URL without Pulse or Cloudflare credentials.

---

## Public accessibility

Podcast publication is pull-based.

Pulse does not push audio bytes into Spotify.

Instead, podcast clients fetch:

```text
RSS feed
    ↓
episode enclosure URLs
    ↓
audio
```

The public podcast origin must therefore allow anonymous HTTP access to the feed and its media.

A successful V1 publication requires at least:

```text
GET <feed-url>
    → 200

HEAD / GET <audio-url>
    → 200
```

Neither request should require:

```text
Cloudflare API credentials
Pulse application credentials
authenticated Worker access
```

The feed's enclosure URL must resolve to the same audio object represented by the stored episode audio reference.

---

## MIME types

Pulse V1 publishes MP3 episode audio.

The expected public content types are:

```text
RSS
    application/rss+xml

episode audio
    audio/mpeg
```

The RSS enclosure also identifies the media as:

```xml
type="audio/mpeg"
```

The configured artwork URL must resolve to an actual public image, but artwork upload and artwork content-type management are not owned by the V1 publication pipeline.

---

## Podcast-client compatibility

Pulse publishes a standard RSS podcast feed rather than integrating episode publication separately with each podcast application.

Conceptually:

```text
Pulse
    ↓
public RSS
    ↓
Spotify / compatible podcast client
    ↓
client reads enclosure
    ↓
public MP3
```

This keeps the publication boundary provider-independent.

Spotify is therefore a consumer of Pulse's RSS feed rather than part of the episode-generation workflow.

Once a show has been registered with a podcast client, subsequent Pulse publications update the same RSS feed. The client can then discover new episode items through its normal feed-refresh process.

Pulse does not control when an external podcast client refreshes or caches that feed.

---

## Publication is the episode success boundary

Audio persistence alone does not mean that an episode has been published.

For example:

```text
audio synthesized
    ↓
audio stored in R2
    ↓
publication fails
```

At this point an R2 object may exist, but Pulse has not completed the episode-producing business path.

The episode becomes successfully published only when the publication stage completes and returns its `PublicationResult`.

This distinction is what allows Pulse to keep expensive generated audio without falsely recording a failed publication as successful consumption.

---

## Publish before signal commit

Signal history is deliberately committed **after** successful publication.

The episode-producing path is:

```text
select signals
    ↓
generate episode
    ↓
store audio
    ↓
publish episode
    ↓
CommitSignalsNode
```

not:

```text
select signals
    ↓
commit signals
    ↓
generate / publish episode
```

This ordering protects an important invariant:

> A failed run must not make source material appear successfully consumed by that pipeline.

Consider:

```text
signals selected
    ↓
signal history committed
    ↓
RSS publication fails
```

A later fresh run could then exclude those signals even though no successful episode was ever published.

Pulse avoids that state by making successful publication the prerequisite for signal-history commit on the episode-producing path.

---

## `CommitSignalsNode`

After `PublishEpisodeNode` succeeds, LangGraph advances to `CommitSignalsNode`.

The commit stage uses the checkpointed signal state:

```text
unseen_signals
embedded_signals_by_id
processed_signals_by_id
```

and stable `signal_id` values to identify the signals accepted by the run.

It then updates two forms of pipeline-scoped history:

```text
D1
    exact signal history

Vectorize
    semantic signal history
```

Publication state and signal-consumption state therefore remain separate concerns:

```text
PodcastPublisher
    → episode publication state

CommitSignalsNode
    → pipeline consumption history
```

The publisher does not update signal history itself.

This keeps the ordering explicit in LangGraph and prevents the publication service from becoming coupled to semantic processing.

---

## `NO_CONTENT` and publishing

The successful `NO_CONTENT` path does not invoke `PodcastPublisher`.

There is no:

```text
audio object
episode publication record
new RSS item
```

for that run.

`CompleteWithoutEpisodeNode` sets `workflow_outcome` to `NO_CONTENT` and the graph goes directly to `END`.

It does not call `CommitSignalsNode`. A no-content run does not write exact signal history or semantic signal history.

`PUBLISHED` is the only outcome that reaches signal commit, and only after `publish_episode`.

---

## Failure and resume behavior

Publication sits near the end of an expensive workflow, so restartability is particularly important.

### Failure before publication

Suppose generation and audio production succeed but publication fails:

```text
EpisodeScript
    ↓
EpisodeMetadata
    ↓
audio stored in R2
    ↓
checkpoint
    ↓
PublishEpisodeNode
    ↓
failure
```

Signal history has not been committed.

Resuming the same logical `run_id` restores the persisted workflow state, including the same episode identity and stored audio reference.

Conceptually:

```text
resume same run_id
    ↓
restore checkpoint
    ↓
reuse stored episode audio
    ↓
retry publication
```

Pulse does not need to resynthesize the episode simply because RSS publication failed.

### Failure during publication

Publication itself involves durable side effects.

For example, a failure may occur after one external write but before the entire node completes:

```text
publication record written
    ↓
RSS upload fails
```

LangGraph cannot roll back the completed external write.

Publication is therefore designed around stable episode identity and replay-safe operations so that retrying the same logical episode repairs or reproduces the desired final state instead of creating a second episode.

The desired state remains:

```text
one show
+
one episode_id
+
one GUID
+
one publication record
+
one RSS item
```

### Failure after publication, before signal commit

A different boundary exists after publication succeeds:

```text
PublishEpisodeNode
    ↓
publication checkpointed
    ↓
CommitSignalsNode
    ↓
failure
```

The episode is already legitimately public.

The run should resume from the same logical execution and retry signal-history commit rather than republishing a new episode.

Signal persistence is itself designed to be idempotent so this recovery does not create duplicate history.

This means the two durable concerns can recover independently:

```text
publication
    already complete

signal commit
    retry until complete
```

---

## Why the boundaries are separate

Publishing spans three different kinds of durable state:

```text
R2
    public episode audio
    public RSS feed

D1
    episode publication catalogue

D1 + Vectorize
    pipeline signal history
```

They deliberately do not belong to one giant transaction.

Instead, Pulse relies on:

```text
stable identities
checkpointed workflow state
idempotent writes
ordered side effects
resume of the same logical run
```

The ordering provides the business guarantee that matters:

```text
no successful publication
    → no consumed-signal history

successful publication
    → signal history may be committed
```

---

## Architectural boundaries

The publishing subsystem owns:

```text
episode publication records
public episode URL construction
RSS rendering
RSS publication
podcast GUIDs
podcast-client-facing metadata
```

Audio production owns:

```text
speech synthesis
audio assembly
audio persistence to R2
```

Signal commit owns:

```text
exact consumed history
semantic consumed history
```

The complete end-of-run boundary is:

```text
generation
    ↓
stored episode audio
    +
EpisodeMetadata
    ↓
publishing
    ↓
PublicationResult
    ↓
signal-history commit
    ↓
PUBLISHED
```

The public delivery path is:

```text
D1 publication catalogue
        ↓
RSS renderer
        ↓
R2 rss.xml
        ↓
public_base_url
        ↓
podcast client
        ↓
R2 episode enclosure
```

---

## Related documentation

- [System architecture](../architecture.md) — workflow ordering, checkpointing, and storage boundaries.
- [Generation](generation.md) — metadata generation, audio synthesis, assembly, and R2 audio persistence.
- [Semantic processing](semantics.md) — accepted signals and post-publication signal-history commit.
- [Configuration](../configuration.md) — `PodcastShow`, public URLs, artwork, and feed configuration.
- [Deployment](../deployment.md) — R2 provisioning, public development domains, custom domains, and deployment verification.
- [Operations](../operations.md) — inspecting published runs, public feeds, and production failures.