# Troubleshooting

This guide covers common failures when deploying and operating Pulse.

Start with the symptom you can observe, verify the failing layer, and only then move deeper into the system. Avoid rerunning or redeploying blindly: Pulse spans several independent layers, and success at one layer does not prove success at another.

For normal operational commands, see [Operations](operations.md). For infrastructure setup and required Cloudflare permissions, see [Deployment](deployment.md).

## Quick triage

| Symptom | Check first |
| --- | --- |
| Spotify does not load or update the show | Fetch the RSS URL directly |
| RSS returns an error | R2 public access, object URL, and domain configuration |
| RSS loads but episode does not play | Fetch the enclosure URL directly |
| Artwork is missing | Fetch the artwork URL directly |
| Browser opens an object but podcast clients reject it | Check `Content-Type` |
| `r2.dev` or custom-domain URL fails | Check R2 public access and configured public base URL |
| Cloudflare reports `no access to service` | Check active credentials, account, and token permissions |
| Wrangler behaves differently from Pulse CLI | Check for a `CLOUDFLARE_API_TOKEN` authentication collision |
| Deployment completes but Pulse verification fails | Investigate the failed verification step rather than redeploying |
| Worker raises `ModuleNotFoundError` or import errors | Check Worker bundle and Pyodide-compatible dependencies |
| Pipeline completes but publishes nothing | Inspect `workflow_outcome` and `no_content_reason` |
| Resume starts incorrectly or cannot find state | Verify the original `run_id` and D1 checkpoint environment |

## Spotify feed is stuck or does not load

Treat Spotify as the final consumer of the publishing chain.

First verify Pulse's RSS feed independently:

```bash
curl -i https://<podcast-host>/shows/<show-id>/rss.xml
```

The request should return a successful HTTP response and XML content.

Then verify that the document itself is well formed:

```bash
curl -fsSL https://<podcast-host>/shows/<show-id>/rss.xml \
  | xmllint --noout -
```

If `xmllint` exits successfully, inspect the latest `<item>`:

```bash
curl -fsSL https://<podcast-host>/shows/<show-id>/rss.xml
```

Check:

- the latest episode is present;
- its `<guid>` is populated and appropriate for that episode;
- the `<enclosure>` URL is correct;
- the enclosure is publicly accessible;
- the artwork URL is publicly accessible;
- publication dates and episode metadata are plausible.

If the RSS URL itself is inaccessible or malformed, the problem is in Pulse's publishing path rather than Spotify.

If the RSS document and every referenced public asset are healthy, avoid repeatedly republishing the same episode merely to force a Spotify refresh. At that point, investigate the feed state on the podcast platform separately.

## RSS is inaccessible

Check the response directly:

```bash
curl -i https://<podcast-host>/shows/<show-id>/rss.xml
```

Useful distinctions include:

- **DNS or connection failure** — investigate the configured public domain.
- **403** — investigate public R2 access or access rules.
- **404** — verify the expected object path and whether publication created the RSS object.
- **5xx** — investigate the serving layer or Cloudflare configuration.
- **200 with unexpected content** — verify the public base URL and object being addressed.

Pulse's show feed is published under:

```text
shows/<show-id>/rss.xml
```

If `publish_episode` completed but this object is missing, inspect the publishing logs and R2 configuration before rerunning the pipeline.

## Audio enclosure is inaccessible

Copy the enclosure URL from the RSS document rather than reconstructing it manually.

Then request it directly:

```bash
curl -I "<audio-url>"
```

If necessary, follow redirects and show the full response:

```bash
curl -L -i "<audio-url>"
```

A published enclosure must be publicly accessible without Cloudflare credentials.

If the object returns 404, determine whether:

1. audio production completed;
2. `publish_episode` received the generated audio artifact;
3. the audio object was written to the expected R2 key;
4. the RSS enclosure points to that same public object.

A valid RSS document does not prove that its enclosure exists.

## Artwork is missing or inaccessible

Take the artwork URL from the RSS document and test it directly:

```bash
curl -I "<artwork-url>"
```

Then inspect the response body if necessary:

```bash
curl -L "<artwork-url>" --output /tmp/pulse-artwork
file /tmp/pulse-artwork
```

Check both availability and media type.

Pulse does not upload artwork during `pulse init`, `pulse deploy`, or episode publication. The RSS document uses the `artwork_url` configured on the show. If that URL fails, correct the show configuration or the host that serves the image.

## Wrong content types

Podcast clients depend on HTTP metadata as well as object contents.

Inspect headers with:

```bash
curl -I "<url>"
```

The response `Content-Type` should match the resource being served.

Typical examples are:

```text
RSS       application/rss+xml
MP3       audio/mpeg
PNG       image/png
JPEG      image/jpeg
```

The exact image type should match the configured artwork file.

Do not assume an object is correctly published merely because a browser displays or downloads it. Browsers are often more tolerant of incorrect media types than podcast clients.

If the body is correct but the header is wrong, inspect the metadata assigned when Pulse writes the object to R2.

## R2 public URL issues

R2 buckets are private unless public access is explicitly configured.

Pulse may publish through either:

- an R2 public development domain; or
- a configured custom domain.

Verify the exact public URL Pulse is configured to generate and request an existing object through that URL.

Do not confuse:

```text
R2 API access
```

with:

```text
public HTTP access to podcast artifacts
```

A Cloudflare API token that can read or write the bucket does not make the bucket publicly accessible.

For development, verify that the bucket's public development URL is enabled.

For production, verify the configured custom domain and its R2 association.

Also confirm that Pulse's configured public base URL matches the access method actually enabled. An object can exist correctly in R2 while RSS still contains unusable URLs because the public base URL is wrong.

See [Deployment](deployment.md) for public-domain configuration.

## Cloudflare reports `no access to service`

Treat this as an authentication, authorization, account, or resource-selection problem first.

Check which account Wrangler is using:

```bash
npx wrangler@latest whoami
```

Then check whether the expected Cloudflare account ID is configured.

Do not print API tokens while debugging.

For Pulse-specific credentials, safely check whether relevant variables are set:

```bash
env \
  | grep -E '^(PULSE_CLOUDFLARE_API_TOKEN|CLOUDFLARE_API_TOKEN|CLOUDFLARE_ACCOUNT_ID)=' \
  | sed 's/=.*/=<set>/'
```

Then verify:

1. the resource belongs to the expected Cloudflare account;
2. the configured account ID is correct;
3. the active token has the permissions documented in [Deployment](deployment.md);
4. the token is not restricted to a different account or resource;
5. Wrangler is not unintentionally using a different credential from Pulse.

Do not solve authorization failures by broadening a token indiscriminately. Compare its permissions against Pulse's documented minimum deployment permissions.

## Missing or incorrect Cloudflare token permissions

Pulse touches multiple Cloudflare services, so one successful API operation does not prove the token can perform every deployment operation.

The deployment token must have the permissions described in [Deployment](deployment.md) for the resources Pulse manages, including the required Workers, D1, R2, and Vectorize access.

When a particular operation fails, use the affected resource to narrow the permission problem.

For example:

```text
D1 creation/migration fails
    → inspect D1 permissions

R2 configuration fails
    → inspect R2 permissions

Vectorize provisioning fails
    → inspect Vectorize permissions

Worker or Workflow deployment fails
    → inspect Workers permissions
```

Also verify that the token belongs to the same Cloudflare account identified by the deployment configuration.

## Wrangler authentication-token collision

Pulse deliberately distinguishes between:

```text
PULSE_CLOUDFLARE_API_TOKEN
```

and:

```text
CLOUDFLARE_API_TOKEN
```

`PULSE_CLOUDFLARE_API_TOKEN` belongs to Pulse's Cloudflare API integration.

`CLOUDFLARE_API_TOKEN` is recognized directly by Wrangler and can override the OAuth credentials established by:

```bash
npx wrangler@latest login
```

This creates an easy failure mode:

1. you successfully authenticate Wrangler with your Cloudflare account;
2. an old or restricted `CLOUDFLARE_API_TOKEN` remains exported in your shell;
3. Wrangler uses that token instead of the OAuth session;
4. commands fail with unexpected permission or service-access errors.

Check whether the environment variable exists without printing its value:

```bash
if [ -n "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "CLOUDFLARE_API_TOKEN is set"
else
  echo "CLOUDFLARE_API_TOKEN is not set"
fi
```

You can also inspect the authentication type Wrangler selected without displaying the token itself:

```bash
npx wrangler@latest auth token --json | jq '{type}'
```

If you intend Wrangler to use its OAuth login and an unrelated `CLOUDFLARE_API_TOKEN` is exported, remove it from the current shell:

```bash
unset CLOUDFLARE_API_TOKEN
```

Then retry:

```bash
npx wrangler@latest whoami
```

Keep the two environment-variable responsibilities separate. Do not rename Pulse's token to `CLOUDFLARE_API_TOKEN` merely because Wrangler recognizes that name.

## Deployment succeeds but verification fails

A successful Wrangler deployment means Cloudflare accepted the Worker deployment.

It does not prove that the complete Pulse installation is operational.

Pulse's post-deploy verification exists to catch failures such as:

- missing bindings;
- inaccessible resources;
- incorrect Workflow configuration;
- Worker startup/import failures;
- incorrect public R2 configuration;
- missing secrets.

When deployment succeeds but verification fails, use the failed verification step as the starting point.

Tail the Worker:

```bash
npx wrangler@latest tail pulse-worker \
  --config workers/cloudflare/wrangler.jsonc
```

Inspect Workflow availability:

```bash
npx wrangler@latest workflows instances list pulse-pipeline \
  --config workers/cloudflare/wrangler.jsonc
```

Then test the specific resource that verification reported as unhealthy.

Do not repeatedly run deployment until verification happens to pass. That can obscure the original failure and create unnecessary infrastructure changes.

## Worker or Pyodide import issues

Pulse's Cloudflare Worker runs in Cloudflare's Python Worker environment rather than ordinary local CPython.

A package importing successfully on your development machine does not guarantee that it can be imported by the deployed Worker.

Typical symptoms include:

```text
ModuleNotFoundError
ImportError
```

or an exception during Worker startup before Pulse reaches the scheduler or Workflow runtime.

First tail the Worker:

```bash
npx wrangler@latest tail pulse-worker \
  --config workers/cloudflare/wrangler.jsonc
```

Determine which category the missing import belongs to:

1. Pulse's own package was not included correctly in the Worker bundle;
2. a Python dependency was omitted from the generated dependency set;
3. the dependency is unavailable or incompatible with the Worker/Pyodide environment;
4. a module path changed during a refactor but the Worker bundle still references the old path.

Do not fix this by adding arbitrary files to the deployed Worker.

Trace the dependency through Pulse's deployment build pipeline and generated Worker bundle. See [Deployment](deployment.md) for the wheel and Pyodide dependency flow.

## Bundle or dependency issues

When the Worker bundle fails before application execution, separate a **Pulse packaging problem** from a **third-party compatibility problem**.

Check:

- the Pulse wheel was rebuilt from the current source;
- the generated Worker bundle contains the expected Pulse package;
- generated dependency declarations match the application dependencies;
- imports use the current package paths;
- dependencies required only by local tooling have not accidentally entered the Worker runtime;
- newly introduced libraries are compatible with the Cloudflare Python runtime.

If a recent refactor moved a module, search the generated bundle and source tree for the old import path before assuming Cloudflare is serving an old deployment.

A clean local import under CPython is not sufficient evidence that the Worker bundle is valid.

## Pipeline unexpectedly returns no episode

First determine whether Pulse actually failed.

Inspect the Workflow result or run logs for:

```text
workflow_outcome = no_content
```

A `no_content` outcome is successful. It means the graph intentionally terminated without producing an episode.

Inspect:

```text
no_content_reason
```

to determine which stage stopped the run.

Current no-content conditions include:

```text
no_unseen_signals
no_semantically_unique_signals
no_processed_signals
no_themed_clusters
```

Use the reason to narrow investigation.

### `no_unseen_signals`

Start with retrieval and exact deduplication.

Check whether:

- the configured X list returned source material;
- retrieved conversations were reconstructed successfully;
- the material had already been persisted as consumed signal history;
- retrieval limits or source availability unexpectedly produced an empty input.

Do not immediately clear deduplication state simply to force content through.

### `no_semantically_unique_signals`

Retrieval produced unseen input, but semantic processing determined that nothing remained after semantic deduplication.

Inspect semantic-processing logs and Vectorize access.

### `no_processed_signals`

Signals reached post-processing but none remained eligible for the episode.

Inspect scoring, filtering, and augmentation results.

### `no_themed_clusters`

Processed signals existed, but grouping did not produce usable themed clusters.

Inspect the grouping node and its result summary.

The correct response to unexpected `no_content` is to diagnose the stage represented by the reason—not to treat the successful early exit as a Cloudflare failure.

## Checkpoint and resume issues

Pulse identifies a logical run by `run_id`.

That same value is used as the LangGraph `thread_id`.

A scheduled Cloudflare execution uses one identity inside the Worker:

```text
Cloudflare Workflow instance ID
            =
Pulse run_id
            =
LangGraph thread_id
```

That checkpoint is written to D1 by `WorkerCloudflareD1Saver` on the `PULSE_DB` binding. Workflow step retries call `RunManager.run_or_resume` with the same instance id. `pulse run resume` does not read those D1 checkpoints.

`pulse run resume` resumes a local CLI run from the SQLite checkpointer:

```bash
pulse run resume <run-id> --pipeline-id <pipeline-id>
```

The database path is `PULSE_CHECKPOINT_DATABASE_PATH`. When that variable is unset, local runs use `runtime/pulse-checkpoints.sqlite`.

If local resume cannot find the expected state, verify all of the following:

1. you are using the original local `run_id`, not an episode ID;
2. `--pipeline-id` is the pipeline that owns that run;
3. `PULSE_CHECKPOINT_DATABASE_PATH` points at the SQLite file that recorded the run;
4. a checkpoint was actually persisted before the failure;
5. you have not accidentally started a fresh run with a new `run_id`.

### Inspect checkpoint storage

Start by examining the remote D1 schema rather than decoding checkpoint blobs manually:

```bash
npx wrangler@latest d1 execute <database-name> \
  --remote \
  --config workers/cloudflare/wrangler.jsonc \
  --command "PRAGMA table_info(checkpoints);"
```

Then confirm that checkpoints exist for the logical run using the schema currently deployed.

The LangGraph checkpoint payload itself is serialized. Raw checkpoint or write bytes are not intended to be interpreted directly from the CLI.

The important operational questions are:

```text
Does this thread_id exist?
What is its latest checkpoint?
Did the failed execution reach the checkpoint expected from its logs?
```

If the local run ID has no SQLite checkpoint, `pulse run resume` cannot reconstruct state that was never persisted. A scheduled production run is recovered by the Cloudflare Workflow step retry against D1, not by the local resume command.

### Resume appears to repeat work

A resumed graph may re-enter work around the last durable checkpoint depending on where the failure occurred.

Do not assume every external side effect is exactly-once merely because graph state is checkpointed.

In particular, investigate the existing run before manually repeating publication-related operations.

Pulse intentionally commits consumed signal history only after successful publication, but checkpoint durability and external side-effect idempotency are separate concerns.

See [Architecture](architecture/) for the checkpoint/retry model and [Operations](operations.md) for normal resume behavior.

## Useful diagnostic commands

### Check Pulse configuration

```bash
pulse schedule get <pipeline-id>
```

### Start a controlled manual run

```bash
pulse run <pipeline-id>
```

### Resume an existing logical run

```bash
pulse run resume <run-id> --pipeline-id <pipeline-id>
```

### Check Wrangler identity

```bash
npx wrangler@latest whoami
```

### Check which authentication type Wrangler selected

```bash
npx wrangler@latest auth token --json | jq '{type}'
```

Do not print or paste the full token response.

### Tail the deployed Worker

```bash
npx wrangler@latest tail pulse-worker \
  --config workers/cloudflare/wrangler.jsonc
```

### List Workflow instances

```bash
npx wrangler@latest workflows instances list pulse-pipeline \
  --config workers/cloudflare/wrangler.jsonc
```

### List errored Workflow instances

```bash
npx wrangler@latest workflows instances list pulse-pipeline \
  --status errored \
  --config workers/cloudflare/wrangler.jsonc
```

### Inspect the latest Workflow instance

```bash
npx wrangler@latest workflows instances describe pulse-pipeline latest \
  --config workers/cloudflare/wrangler.jsonc
```

### Inspect one Workflow instance as JSON

```bash
npx wrangler@latest workflows instances describe pulse-pipeline <instance-id> \
  --config workers/cloudflare/wrangler.jsonc \
  --json
```

### Inspect the remote D1 schema

```bash
npx wrangler@latest d1 execute <database-name> \
  --remote \
  --config workers/cloudflare/wrangler.jsonc \
  --command ".tables"
```

```bash
npx wrangler@latest d1 execute <database-name> \
  --remote \
  --config workers/cloudflare/wrangler.jsonc \
  --command "PRAGMA table_info(checkpoints);"
```

### Inspect a public resource

```bash
curl -L -i "<url>"
```

For headers only:

```bash
curl -I "<url>"
```

### Validate RSS syntax

```bash
curl -fsSL https://<podcast-host>/shows/<show-id>/rss.xml \
  | xmllint --noout -
```

## Debugging order

When the source of a failure is unclear, work from the outside inward:

```text
Public RSS / audio / artwork
            ↓
Publishing and R2
            ↓
Pulse run outcome
            ↓
LangGraph node logs
            ↓
Checkpoint state
            ↓
Cloudflare Workflow attempt
            ↓
Scheduler
            ↓
Deployment / bindings / credentials
```

Do not start at the deepest layer unless the observable symptom points there.

The goal is to identify the first boundary where expected behavior stops. Once that boundary is known, the corresponding logs or configuration usually provide a much smaller problem to investigate.