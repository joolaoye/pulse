# Getting Started

This guide takes a fresh Pulse checkout through its first deployed podcast pipeline.

By the end, you will have:

- a configured Pulse installation;
- a podcast show;
- a generation pipeline backed by a curated X list;
- a persisted schedule;
- a deployed Cloudflare runtime; and
- a public RSS feed that can be added to Spotify or another podcast client.

For the complete configuration reference, see [Configuration](configuration.md). For Cloudflare setup and deployment details, see [Deployment](deployment.md).

## Prerequisites

Pulse requires:

- Python, using the version supported by the repository's `pyproject.toml`;
- [`uv`](https://docs.astral.sh/uv/);
- Node.js and npm;
- a Cloudflare account;
- an X developer account and bearer token;
- an Anthropic API key;
- a Voyage AI API key; and
- an ElevenLabs API key.

You also need a Cloudflare API token with the permissions required to provision and deploy Pulse. See [Deployment](deployment.md) for the current permission set.

Your podcast configuration will reference one or more ElevenLabs voice IDs, so choose or create those voices before creating a pipeline.

## 1. Clone and install

Clone the repository and enter it:

```bash
git clone <repository-url>
cd pulse
```

### macOS / Linux

```bash
bash bootstrap.sh
```

### Windows PowerShell

```powershell
.\bootstrap.ps1
```

The bootstrap step runs `uv sync`, which installs the locked Python dependencies into `.venv`, then installs the repository's Node dependencies and makes the project-local Wrangler tooling available.

It does not provision Cloudflare resources or ask for podcast/provider configuration.

Verify the CLI:

```bash
pulse --help
```

## 2. Initialize Pulse

Run:

```bash
pulse init
```

`pulse init` configures a Pulse installation. It collects the provider and Cloudflare credentials Pulse needs, prepares local configuration, and provisions or reuses the required Cloudflare resources.

The initialization flow covers the infrastructure used by Pulse, including:

- Cloudflare D1;
- Cloudflare R2;
- Cloudflare Vectorize; and
- the D1 migrations required by the current application.

Initialization is intended to be safe to repeat: existing resources are reused or validated rather than blindly recreated.

Provider secrets belong in local/deployed configuration, not in committed repository files. Do not commit `.env`, generated Wrangler configuration containing installation-specific values, or provider credentials.

For the exact environment and Cloudflare resource model, see [Deployment](deployment.md).

## 3. Create a podcast show

A `PodcastShow` describes **where episodes are published** and how the podcast appears to clients.

Create one with:

```bash
pulse show create
```

The command prompts for the show's public metadata, including its ID, title, description, author, website, artwork, category, public base URL, and RSS object key.

Two fields are especially important for publishing:

- `public_base_url` — the public origin used to build RSS and media URLs;
- `feed_object_key` — the object-storage key for the show's RSS file.

For example:

```text
Public base URL: https://<your-public-podcast-host>
Feed object key: shows/my-show/rss.xml
```

The resulting feed URL is built from those two values:

```text
https://<your-public-podcast-host>/shows/my-show/rss.xml
```

The artwork URL must also be publicly reachable. Pulse publishes episode audio and the RSS feed, but the artwork URL you configure must point to a real public image before podcast-directory submission.

After creation, Pulse prints the show's feed URL. You can retrieve it again with:

```bash
pulse show get <show-id>
```

The show details include the `Public Base URL`, `Feed Object Key`, and resolved `Feed URL`.

For all show fields, see [Configuration](configuration.md).

## 4. Create the pipeline configuration

A `PodcastPipeline` describes **how episodes are generated**.

Before creating one, prepare:

1. an interest profile in Markdown; and
2. a podcast configuration JSON file containing the podcast profile, speakers, and speaker-to-voice bindings.

The interest profile describes what Pulse should care about when scoring retrieved signals. The podcast configuration defines the editorial personality and voices used to generate the episode.

A minimal podcast configuration can look like this:

```json
{
  "podcast_profile": {
    "name": "Pulse Daily",
    "purpose": "Help listeners quickly understand the most relevant technology and startup developments of the day.",
    "target_audience": "Software engineers, technical founders, and technology professionals who are comfortable with technical concepts but want concise context and analysis.",
    "editorial_style": "Prioritize technically substantive developments, explain why they matter, connect related stories, and avoid hype-driven framing.",
    "conversational_style": "Natural, analytical, and conversational, with speakers challenging assumptions and explaining ideas clearly without sounding scripted."
  },
  "speakers": [
    {
      "speaker_id": "host",
      "display_name": "Host",
      "podcast_role": "Primary host",
      "persona": "Curious, analytical, and skeptical of hype.",
      "expertise": [
        "software engineering",
        "technology",
        "startups"
      ],
      "speaking_style": "Conversational, concise, and direct."
    }
  ],
  "speaker_voice_bindings": [
    {
      "speaker_id": "host",
      "voice_id": "5u41aNhyCU6hXOcjPPv0"
    }
  ]
}
```

For example, save that as:

```text
config/podcast.json
```

A matching interest profile can be much simpler:

```markdown
# Interests

I am interested in:

- software engineering
- AI infrastructure
- developer tools
- startups
- cloud platforms

Prefer technically substantive stories over hype.
```

For example:

```text
config/interests.md
```

The `speaker_id` values in `speaker_voice_bindings` must match speakers defined in `speakers`. The `voice_id` is the ElevenLabs voice Pulse should use for that speaker.

See [Configuration](configuration.md) for the complete file formats and field reference.

Create the pipeline with:

```bash
pulse pipeline create <interest-profile.md> <podcast-configuration.json>
```

Pulse then prompts for:

- pipeline ID;
- show ID;
- X list ID; and
- target episode duration in seconds.

You can also provide those values explicitly:

```bash
pulse pipeline create \
  ./config/interests.md \
  ./config/podcast.json \
  --pipeline-id my-pipeline \
  --show-id my-show \
  --x-list-id <x-list-id> \
  --duration 1200
```

A newly created pipeline is enabled by default.

Verify it:

```bash
pulse pipeline get my-pipeline
```

The pipeline should reference the show you created and the curated X list you want Pulse to read.

## 5. Set a schedule

Schedules are persisted by Pulse rather than encoded as one Cloudflare Cron Trigger per pipeline.

For example, to run a pipeline every day at 6:30 AM in the `America/Chicago` timezone:

```bash
pulse schedule set my-pipeline \
  --time 06:30 \
  --timezone America/Chicago
```

Verify the persisted schedule:

```bash
pulse schedule get my-pipeline
```

Changing a pipeline schedule does not require redeploying the Worker.

For scheduling semantics, timezones, and the scheduler execution model, see [Scheduling](architecture/scheduling.md).

## 6. Deploy Pulse

Deploy the Cloudflare runtime:

```bash
pulse deploy
```

The deployment command owns the production build and deployment path. It prepares a fresh Pulse wheel, builds the Worker-compatible Python dependencies, validates the generated Wrangler configuration, deploys the required runtime secrets and Worker/Workflow configuration, and verifies the resulting deployment.

You should not need to manually run the Worker dependency build or call Wrangler directly for a normal deployment.

See [Deployment](deployment.md) for the full build, permissions, secret, and verification flow.

## 7. Verify the public feed

Once an episode has been published, retrieve the show's feed URL:

```bash
pulse show get my-show
```

Open the reported `Feed URL` without authentication.

A working public podcast feed should:

- return successfully over HTTPS;
- return RSS/XML content;
- reference a publicly reachable artwork URL; and
- contain public audio enclosure URLs for published episodes.

You can also open an episode enclosure URL directly to verify that the MP3 is reachable without Cloudflare credentials.

If the feed, artwork, or audio is not publicly accessible, see [Troubleshooting](troubleshooting.md).

## 8. Add the feed to Spotify or another client

Pulse publishes standard podcast RSS rather than using a custom listening application.

Use the show's public feed URL with any compatible podcast client or directory.

For Spotify, submit the RSS feed through Spotify for Creators as an existing podcast feed. Spotify must be able to fetch the RSS document, artwork, and every episode enclosure URL without authentication.

Once the feed is accepted, future episodes published by Pulse appear through the same RSS feed.

## What to expect from the first run

A scheduled occurrence launches the configured pipeline through the deployed Cloudflare runtime.

A content-producing run moves through the high-level flow:

```text
X retrieval
→ ingestion
→ semantic processing
→ relevance filtering
→ grouping
→ episode planning
→ script + metadata
→ audio production
→ publishing
→ RSS
```

The first full run can take several minutes because it performs external retrieval, multiple generation stages, text-to-speech, audio assembly, and publication.

A run may also complete successfully without publishing an episode when no sufficiently new and relevant signals survive filtering. That is expected behavior rather than a deployment failure.

For logs, workflow inspection, and deployed runtime checks, see [Operations](operations.md).

## Next steps

- [Configuration](configuration.md) — shows, pipelines, interests, speakers, voices, and schedules.
- [Deployment](deployment.md) — Cloudflare permissions, resources, secrets, build, and deployment.
- [Architecture](architecture.md) — how Pulse is structured end to end.
- [Operations](operations.md) — inspect schedules, runs, logs, workflows, and published feeds.
- [Troubleshooting](troubleshooting.md) — diagnose setup, deployment, RSS, audio, and podcast-client problems.
