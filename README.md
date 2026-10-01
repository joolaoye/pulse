# Pulse

**Turn the feeds you curate into podcasts you actually want to listen to.**

Pulse transforms a curated X list into a personalized podcast. It finds new and relevant ideas, removes repeated noise, groups related stories, plans and writes a coherent episode, synthesizes the audio, and publishes a standard podcast RSS feed that can be consumed by Spotify or another compatible podcast client.

🎧 **[Listen to Pulse on Spotify](https://open.spotify.com/show/033expZMk082DlYDGaAJ6c)**

<p align="center">
  <img
    src="docs/assets/pulse-architecture.svg"
    alt="Pulse architecture"
    width="100%"
  />
</p>

## Why Pulse?

Social feeds are valuable because they contain people and topics you deliberately chose to follow. The problem is the interface: staying informed usually means opening an app, scrolling through noise, and repeatedly checking for updates.

Pulse separates the **source** from the **interface**.

You choose the sources and the topics you care about. Pulse handles retrieval, filtering, synthesis, audio generation, and publishing. The result arrives like any other podcast.

## How it works

At a high level:

```text
Curated X list
      ↓
Retrieve conversations and context
      ↓
Deduplicate and score against your interests
      ↓
Group related signals into themes
      ↓
Plan and write an episode
      ↓
Generate speech
      ↓
Publish audio + RSS
      ↓
Spotify / podcast client
```

Pulse currently uses:

- **X** for source retrieval
- **Voyage AI** for embeddings
- **Anthropic** for theme extraction, planning, scripting, and metadata
- **ElevenLabs** for text-to-speech
- **Cloudflare Workers and Workflows** for scheduled and durable execution
- **Cloudflare D1** for configuration, workflow state, publication metadata, and signal history
- **Cloudflare Vectorize** for semantic history
- **Cloudflare R2** for episode audio and RSS feeds

For the full system design, see the [architecture documentation](docs/architecture.md).

## Quick start

### Requirements

Pulse currently requires:

- Python
- [`uv`](https://docs.astral.sh/uv/)
- Node.js / npm
- a Cloudflare account
- X API credentials
- an Anthropic API key
- a Voyage AI API key
- an ElevenLabs API key

Cloudflare is used for the production runtime, persistence, vector storage, and podcast publishing.

The exact Cloudflare API-token permissions are documented in the [deployment guide](docs/deployment.md).

### Install

After cloning the repository:

**macOS / Linux**

```bash
bash bootstrap.sh
```

**Windows PowerShell**

```powershell
.\bootstrap.ps1
```

Verify that the CLI is available:

```bash
pulse --help
```

### Initialize Pulse

```bash
pulse init
```

Initialization collects the provider and Cloudflare configuration Pulse needs and prepares the required infrastructure.

### Create a show

A **show** represents the podcast that listeners subscribe to.

```bash
pulse show create
```

### Create a pipeline

A **pipeline** defines how Pulse generates episodes: its source list, interests, speakers, voices, and generation configuration.

```bash
pulse pipeline create
```

### Schedule the pipeline

```bash
pulse schedule set <pipeline-id>
```

Pipeline schedules are persisted by Pulse. Updating a schedule does not require redeploying the Worker.

### Deploy

```bash
pulse deploy
```

Pulse builds the Worker, deploys its runtime secrets, configures the Cloudflare Workflow and scheduler, and verifies the resulting deployment.

A published show's RSS feed follows the form:

```text
https://<public-podcast-host>/shows/<show-id>/rss.xml
```

The feed and its audio enclosures must be publicly accessible so podcast clients such as Spotify can ingest them.

For a complete walkthrough, see [Getting started](docs/getting-started.md) and [Deployment](docs/deployment.md).

## Cost

Pulse uses paid APIs for source retrieval, language-model generation, and speech synthesis. Embedding and Cloudflare costs are usually small at personal scale, but provider pricing can change.

A useful way to estimate a run is to start from a concrete workload. For an **18–20 minute episode** that retrieves **50 X posts plus 10 additional reply/context posts**, a conservative budget is:

| Provider | Assumption | Estimated cost |
| --- | --- | ---: |
| X | 60 unique post reads × $0.005/read | **~$0.30** |
| Anthropic | Multi-stage planning, scripting, polish, and metadata | **~$4.50–5.00** |
| ElevenLabs | 18–20 minutes of dialogue at roughly $0.10/minute | **~$1.80–2.00** |
| Voyage AI | Up to ~100K embedded tokens with `voyage-4` | **< $0.01** before free allowance |
| **Variable total** | | **~$6.60–7.30 / episode** |

The Anthropic figure is intentionally an upper-budget estimate rather than a hard cap. It assumes roughly **1.35–1.5 million aggregate input tokens** and **30–35K output tokens** across the generation pipeline at a conservative Sonnet-class rate. Pulse uses cheaper models for some stages, so real usage can be lower.

Voyage AI currently includes a large free token allowance for `voyage-4`, so embedding cost is typically effectively zero for a personal Pulse deployment.

Cloudflare is mostly a fixed infrastructure cost at this scale. The Workers Paid plan starts at **$5/month**, and a personal Pulse workload should generally remain within the included Workers, Workflows, D1, and R2 usage allowances.

Using the upper end of the estimate:

- **Weekly** generation (~4–5 episodes/month): roughly **$31–42/month**, including the Cloudflare base plan.
- **Daily** generation (~30 episodes/month): roughly **$203–224/month**, including the Cloudflare base plan.

These are planning estimates, not guarantees. Actual cost depends on retrieval volume, conversation hydration, how many signals survive filtering, model selection, generated episode length, retries, and provider pricing.

## Architecture

Pulse separates three core concepts:

### Podcast Show

The podcast identity and publication destination.

A show owns things such as its public feed, artwork, and published episodes.

### Podcast Pipeline

The configuration used to generate episodes.

A pipeline defines things such as:

- source X list
- interest profile
- podcast profile
- speakers and voice bindings
- target episode duration
- generation configuration

Multiple pipelines can be configured independently.

### Schedule

When a pipeline should run.

Schedules are stored independently from the Cloudflare deployment, so changing when a pipeline runs does not require redeploying Pulse.

Pulse can be executed manually through the CLI or automatically through Cloudflare.

Long-running runs are checkpointed and resumable, allowing interrupted executions to continue without repeating completed work.

For the deeper system design, including retrieval, semantic processing, generation, publishing, scheduling, checkpointing, and provider boundaries, see [Architecture](docs/architecture.md).

## Documentation

### Using Pulse

- [Getting started](docs/getting-started.md)
- [Configuration](docs/configuration.md)
- [Deployment](docs/deployment.md)
- [Operations](docs/operations.md)
- [Troubleshooting](docs/troubleshooting.md)

### Architecture

- [Architecture overview](docs/architecture.md)
- [Retrieval](docs/architecture/retrieval.md)
- [Semantic processing](docs/architecture/semantics.md)
- [Generation](docs/architecture/generation.md)
- [Publishing](docs/architecture/publishing.md)
- [Scheduling](docs/architecture/scheduling.md)

## Contributing

Contributions are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow and the contributor documentation under [`docs/internal/`](docs/internal/).

## License

A license has not yet been selected for Pulse.
