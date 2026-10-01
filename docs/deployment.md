# Deployment

Pulse's production runtime is deployed to Cloudflare.

The normal lifecycle is:

```text
pulse init
    ↓
provision / reuse Cloudflare resources
    ↓
generate installation-specific Wrangler configuration
    ↓
configure shows, pipelines, and schedules
    ↓
pulse deploy
    ↓
build + validate + deploy Worker runtime
    ↓
verify deployed Worker
```

![Pulse deployment architecture](assets/pulse-deploy-architecture.svg)

This document covers the Cloudflare resources, permissions, secrets, build process, public podcast storage, and deployment lifecycle used by Pulse.

For the first-run walkthrough, see [Getting started](getting-started.md).

## Cloudflare resources

A production Pulse installation uses:

| Resource | Purpose |
| --- | --- |
| Cloudflare Workers | Python runtime and scheduled entrypoint |
| Cloudflare Workflows | Durable outer execution for scheduled Pulse runs |
| Cloudflare D1 | Application configuration, schedules, publication data, signal state, and LangGraph checkpoints |
| Cloudflare Vectorize | Semantic signal history and deduplication |
| Cloudflare R2 | Episode audio and RSS feeds. Show artwork is a public URL on the show, not an object Pulse uploads. |
| Cron Trigger | One recurring scheduler heartbeat for all persisted pipeline schedules |

Pulse does **not** create one Cloudflare Cron Trigger per podcast pipeline.

The deployed Worker has one recurring scheduler heartbeat:

```text
*/5 * * * *
```

Pipeline schedules live in D1. The scheduler wakes periodically, finds due enabled pipelines, and dispatches Cloudflare Workflow instances.

For the scheduling model, see [Scheduling](architecture/scheduling.md).

## Cloudflare API token

Pulse uses an API token rather than `wrangler login` / browser OAuth.

For a fresh installation, create an account-scoped Cloudflare API token with access to the account where Pulse will run.

### Required permissions

Cloudflare introduced product-scoped Developer Platform roles in 2026. For a fresh Pulse installation, the recommended policy is:

| Product scope | Role | Why Pulse needs it |
| --- | --- | --- |
| Workers | **Admin** | Create the Worker on the first deploy, then update deployments, schedules, Workflow configuration, and secrets |
| D1 | **Admin** | Discover or create the Pulse database and apply schema changes |
| R2 | **Admin** | Discover or create the podcast bucket |
| Vectorize | **Admin** | Discover or create the signal index and its metadata index |

Scope each permission to the Cloudflare account that owns the Pulse installation.

`Workers Admin` is important for a greenfield deployment. Cloudflare's `Editor` role can update an existing Worker, but creating a Worker that does not exist yet requires product-level `Admin`.

Likewise, Pulse initialization may create missing D1, R2, and Vectorize resources. Under Cloudflare's current Developer Platform role model, creating resources requires the product-level `Admin` role.

If you later separate initial provisioning from routine deployment, you can use narrower credentials for existing resources. Pulse's default setup assumes one token can perform the complete `pulse init` + first `pulse deploy` lifecycle.

### Routes and Worker custom domains

The default Pulse deployment does not require a Worker route or Worker custom domain for podcast files.

If you later configure a **Worker** Route or Custom Domain, Cloudflare additionally requires `Workers Routes Write` for the affected zone.

This is separate from attaching a custom domain directly to an R2 bucket.

### Older Cloudflare permission names

Older Cloudflare API-token screens and older documentation may expose legacy permission names such as:

```text
Workers Scripts Write
D1 Write
Workers R2 Storage Write
Vectorize Edit
```

Pulse documentation uses Cloudflare's current Developer Platform role model. For a new installation, prefer a new token using the product-scoped roles above rather than relying on legacy permission names.

Cloudflare permission reference:

- <https://developers.cloudflare.com/workers/authorization/>
- <https://developers.cloudflare.com/workers/authorization/workers/>
- <https://developers.cloudflare.com/fundamentals/api/reference/permissions/>

## `PULSE_CLOUDFLARE_API_TOKEN` vs `CLOUDFLARE_API_TOKEN`

Pulse intentionally uses two names at different boundaries.

### Local Pulse configuration

The local environment stores the Cloudflare credential as:

```env
PULSE_CLOUDFLARE_API_TOKEN=...
```

Pulse owns this name.

Using a Pulse-specific variable prevents an ambient `CLOUDFLARE_API_TOKEN` from silently changing Wrangler authentication outside Pulse's deployment path.

### Wrangler subprocesses

When Pulse invokes Wrangler, it explicitly maps:

```text
PULSE_CLOUDFLARE_API_TOKEN
        ↓
CLOUDFLARE_API_TOKEN
```

for that subprocess.

Wrangler therefore receives the standard Cloudflare variable it expects, while the developer's shell does not need a global `CLOUDFLARE_API_TOKEN`.

You should not need to run:

```text
wrangler login
```

for the normal Pulse lifecycle.

### Worker runtime

The deployed Worker also receives:

```text
CLOUDFLARE_API_TOKEN
```

as a Worker secret because Pulse's runtime uses Cloudflare APIs for its own infrastructure access.

The distinction is:

```text
local .env
    PULSE_CLOUDFLARE_API_TOKEN

Pulse → Wrangler subprocess
    CLOUDFLARE_API_TOKEN

deployed Worker secret
    CLOUDFLARE_API_TOKEN
```

## Secret ownership

Pulse keeps deployment configuration and secret values separate.

Conceptually:

```text
.env
    local installation credentials + resource metadata
        ↓
Pulse deployment inputs
        ↓
temporary secret payload
        ↓
Wrangler
        ↓
Cloudflare Worker secret bindings
```

The temporary secret payload exists only for the deployment operation and is removed after Wrangler finishes.

### Local provider secrets

The local installation needs the provider credentials collected during setup:

```env
X_BEARER_TOKEN=...
ANTHROPIC_API_KEY=...
VOYAGE_API_KEY=...
ELEVENLABS_API_KEY=...
PULSE_CLOUDFLARE_API_TOKEN=...
```

`.env` must remain untracked.

`pulse init` also records non-secret installation values such as the Cloudflare account/resource identifiers required by the application.

### Worker runtime secrets

The deployed Worker receives exactly these runtime secrets:

```text
CLOUDFLARE_API_TOKEN
ANTHROPIC_API_KEY
VOYAGE_API_KEY
X_BEARER_TOKEN
ELEVENLABS_API_KEY
```

These values are deployed through Wrangler's secret mechanism. They are not rendered into the committed template or the generated Wrangler configuration.

### Non-secret Wrangler values

Installation-specific resource values are ordinary Worker configuration, for example:

```text
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_D1_DATABASE_ID
PULSE_VECTORIZE_INDEX_NAME
PULSE_PODCAST_BUCKET_NAME
```

These identify resources; they are not provider credentials.

## What must never appear in `wrangler.jsonc`

Secret **values** must never be written to:

```text
workers/cloudflare/wrangler.jsonc.template
workers/cloudflare/wrangler.jsonc
```

In particular, do not put values for:

```text
PULSE_CLOUDFLARE_API_TOKEN
CLOUDFLARE_API_TOKEN
ANTHROPIC_API_KEY
VOYAGE_API_KEY
X_BEARER_TOKEN
ELEVENLABS_API_KEY
```

inside Wrangler configuration.

Pulse's deployment preflight explicitly checks generated Wrangler configuration for known secret values and fails before deployment if one is found.

The variable names themselves may appear where appropriate. The credential values may not.

## `pulse init`

Run initialization before the first deployment:

```bash
pulse init
```

Initialization owns **installation provisioning**, not the application deployment.

Its responsibilities include:

```text
collect / validate local credentials
        ↓
discover existing Cloudflare resources
        ↓
create missing D1 database
        ↓
apply D1 migrations
        ↓
create / validate Vectorize index
        ↓
ensure Vectorize pipeline_id metadata index
        ↓
create missing R2 podcast bucket
        ↓
write local installation configuration
        ↓
render workers/cloudflare/wrangler.jsonc
```

Initialization is designed to be repeatable.

Existing resources are reused or validated when compatible. Pulse should not blindly create duplicate resources on every run.

The canonical committed Wrangler source is:

```text
workers/cloudflare/wrangler.jsonc.template
```

The installation-specific file is:

```text
workers/cloudflare/wrangler.jsonc
```

The generated file is local installation state. `.gitignore` ignores every `wrangler.jsonc`, including one at the repository root. The template is the only Wrangler file that belongs in git.

## Wrangler configuration

Pulse owns the generated Wrangler configuration.

The important relationship is:

```text
wrangler.jsonc.template
        ↓
Pulse renderer
        ↓
pulse init
        ↓
wrangler.jsonc
```

During deployment, Pulse renders the expected configuration again and verifies that the generated file still matches it.

Manual edits to `workers/cloudflare/wrangler.jsonc` are therefore treated as configuration drift.

If deployment reports that Wrangler configuration is out of sync, regenerate it with:

```bash
pulse init
```

rather than editing the generated file directly.

### Canonical Worker configuration

The production configuration currently includes:

```text
Worker name:
pulse-worker

Worker entrypoint:
entrypoint.py

Compatibility flags:
python_workers
python_workflows

Workflow binding:
PULSE_PIPELINE_WORKFLOW

Workflow class:
PulsePipelineWorkflow

Workflow name:
pulse-pipeline

D1 binding:
PULSE_DB

Scheduler cron:
*/5 * * * *
```

The template also carries the installation-specific Cloudflare account, D1, Vectorize, and R2 identifiers rendered during initialization.

## `pulse deploy`

Deploy with:

```bash
pulse deploy
```

`pulse deploy` owns the production deployment path. A normal user should not need to manually build the Worker, sync Python dependencies, deploy secrets, or call Wrangler.

The deployment sequence is:

```text
deployment preflight
        ↓
validate Wrangler template + generated config
        ↓
clean generated build state
        ↓
build a fresh Pulse wheel
        ↓
assemble Worker / Pyodide Python dependencies
        ↓
validate the Worker bundle
        ↓
prepare temporary Worker secret payload
        ↓
project-local Wrangler deployment
        ↓
remote deployment verification
```

Deployment returns only after the local build and remote verification steps complete successfully.

## Build and Pyodide dependency flow

The main Pulse package is ordinary Python, but Cloudflare Python Workers execute in a Pyodide-based environment.

The deployed Worker therefore needs a Worker-compatible Python bundle.

Conceptually:

```text
src/pulse
    ↓
fresh wheel
    ↓
Worker dependency assembly
    ↓
Pyodide-compatible dependencies + compatibility shims
    ↓
workers/cloudflare/python_modules
    ↓
Wrangler bundle
```

A source-code change to Pulse must therefore produce a fresh wheel before the Worker dependency tree is assembled.

`pulse deploy` handles this sequence for you.

Generated Worker dependencies are build artifacts. They should not be treated as hand-maintained source.

Contributor-level details about compatibility shims and manual Worker development belong in [Development](internal/development.md).

## Deployment preflight

Before mutating the remote Worker, Pulse validates the local deployment state.

Preflight covers concerns such as:

- required deployment inputs are present;
- the canonical Wrangler template contains the required Pulse bindings and compatibility flags;
- generated `wrangler.jsonc` matches what `pulse init` should have produced;
- known secret values have not leaked into Wrangler configuration;
- build inputs and Worker files exist; and
- the Worker bundle can be prepared for deployment.

Wrangler itself is then used as the authoritative Cloudflare deployment tool.

The deployment path uses the repository's project-local Wrangler installation rather than depending on an arbitrary global Wrangler version.

## Worker, Workflow, and Cron deployment

The deployed Worker contains both Pulse's runtime adapter and the scheduler entrypoint.

The deployment establishes:

```text
pulse-worker
    │
    ├── PulsePipelineWorkflow
    │
    ├── PULSE_DB
    │
    ├── PULSE_PIPELINE_WORKFLOW
    │
    └── */5 * * * * scheduler heartbeat
```

The Cron Trigger is **not** the user's podcast schedule.

It only wakes the scheduler. Pipeline-specific schedules remain application state in D1.

This means:

```text
pulse schedule set ...
```

does not require:

```text
pulse deploy
```

after every schedule change.

## Post-deploy verification

Pulse performs remote verification after Wrangler reports a successful deployment.

At a minimum, deployment verification confirms that the expected Worker deployment exists remotely rather than treating successful subprocess exit alone as sufficient proof.

The locally generated configuration is separately validated before deployment, including the expected Worker name, entrypoint, compatibility flags, Workflow binding, D1 binding, scheduler cron, and configured resource identifiers.

A successful deployment therefore means both:

```text
local deployment configuration passed preflight
```

and:

```text
Cloudflare reports the Worker deployment remotely
```

Deployment verification does **not** prove that a full podcast episode can be generated. Use a scheduled or manual pipeline run for that operational smoke test.

See [Operations](operations.md) for Worker logs and Workflow inspection.

## Public R2 access

Creating an R2 bucket does not automatically make podcast files public.

Cloudflare R2 buckets are private by default.

Pulse requires a public origin for podcast delivery because external clients must be able to fetch:

```text
RSS feed
show artwork
episode audio
```

without Cloudflare API credentials.

There are two supported R2 publication approaches.

### Development: `r2.dev`

For development and smoke testing, enable the bucket's **Public Development URL**.

Cloudflare exposes the bucket through a generated `r2.dev` hostname.

You can enable it from the Cloudflare dashboard:

```text
R2
→ select the Pulse podcast bucket
→ Settings
→ Public Development URL
→ Enable
```

Cloudflare also exposes a Wrangler command:

```bash
npx wrangler r2 bucket dev-url enable <bucket-name>
```

The resulting base URL looks like:

```text
https://<generated-id>.r2.dev
```

Use that origin as the show's `public_base_url`.

The `r2.dev` endpoint is intended for development and is rate-limited.

Cloudflare documentation:

<https://developers.cloudflare.com/r2/buckets/public-buckets/>

### Production: custom domain

For a production feed, connect a domain you control directly to the R2 bucket.

For example:

```text
https://podcasts.example.com
```

Cloudflare recommends a custom domain for production rather than relying on the managed `r2.dev` development endpoint.

Once the custom domain is active, configure the show with:

```text
public_base_url:
https://podcasts.example.com
```

The domain must resolve to the same R2 bucket where Pulse publishes the RSS and audio objects.

Changing the public host for an existing show should be done deliberately because RSS, artwork, and enclosure URLs must remain externally reachable.

## Verify podcast assets

After a publishing run, verify the show's feed URL:

```bash
pulse show get <show-id>
```

Then check all three layers independently:

```text
1. RSS URL opens without authentication

2. artwork URL opens without authentication

3. episode enclosure / MP3 URL opens without authentication
```

A feed document that is public while its artwork or audio URLs are private is still unusable by podcast directories.

This is especially important when submitting a feed to Spotify.

For publishing behavior, see [Publishing](architecture/publishing.md).

## Updating an existing deployment

For ordinary source changes:

```bash
pulse deploy
```

is the update path.

Pulse rebuilds the package and Worker dependency bundle before deploying the new Worker version.

You do not need to rerun `pulse init` for every code change.

Run `pulse init` again when installation configuration has changed or when Pulse reports that generated Wrangler configuration is stale, for example after changing Cloudflare resource configuration.

A typical update is:

```text
edit Pulse source
    ↓
run tests
    ↓
pulse deploy
    ↓
remote verification
    ↓
inspect logs / next scheduled run
```

Pipeline content configuration and schedule changes are persisted separately and do not normally require Worker redeployment.

## Common deployment failures

### `No access to specified service`

The Cloudflare token does not have enough Workers access.

For a fresh Worker, use:

```text
Workers → Admin
```

at the Workers product scope for the target account.

An `Editor` role can update an existing Worker but cannot create a new one.

### D1, R2, or Vectorize provisioning fails

Verify that the token has `Admin` access for the corresponding Developer Platform product in the target account.

Fresh initialization may create missing resources, so read-only or editor-only access is not sufficient for the complete greenfield lifecycle.

### Wrangler uses unexpected authentication

Do not rely on an ambient shell-level `CLOUDFLARE_API_TOKEN`.

Pulse stores its token as:

```text
PULSE_CLOUDFLARE_API_TOKEN
```

and explicitly maps it for Wrangler subprocesses.

Check local configuration and rerun through `pulse deploy`.

### Wrangler configuration is out of sync

Do not hand-edit the generated file.

Run:

```bash
pulse init
```

to regenerate:

```text
workers/cloudflare/wrangler.jsonc
```

from the canonical template.

### Worker deploys but post-deploy verification fails

First determine whether Cloudflare actually created a deployment:

```bash
npx wrangler@latest deployments list \
  --name pulse-worker \
  --config workers/cloudflare/wrangler.jsonc
```

If a deployment exists, inspect the current Worker and Workflow state before repeating deployment blindly.

See [Troubleshooting](troubleshooting.md) for deeper diagnostics.

### Podcast feed is not reachable

A successful Worker deployment does not make an R2 bucket public.

Verify that either:

- the bucket's `r2.dev` development URL is enabled; or
- a production custom domain is connected and active.

Then verify that `PodcastShow.public_base_url` points at that public origin.

### Spotify cannot ingest the feed

Verify the entire public asset chain:

```text
RSS
→ artwork
→ episode enclosure
```

All three must be externally reachable.

A valid-looking RSS file that references private or nonexistent media will not produce a working podcast import.

See [Troubleshooting](troubleshooting.md).

## Related documentation

- [Getting started](getting-started.md) — first installation and deployment.
- [Configuration](configuration.md) — shows, pipelines, schedules, and public URLs.
- [Architecture](architecture.md) — system-wide runtime design.
- [Publishing](architecture/publishing.md) — R2, RSS, publication records, and signal commit.
- [Scheduling](architecture/scheduling.md) — persisted schedules and scheduler dispatch.
- [Operations](operations.md) — logs, Workflow inspection, and runtime checks.
- [Troubleshooting](troubleshooting.md) — detailed failure diagnosis.
