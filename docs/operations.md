# Operations

This guide covers day-to-day operation of a deployed Pulse installation: managing schedules, running pipelines manually, observing executions, inspecting Cloudflare Workflow instances, verifying published episodes, and recovering from common failures.

For deployment and infrastructure setup, see [Deployment](deployment.md). For deeper failure investigation, see [Troubleshooting](troubleshooting.md).

## Manage schedules

Pulse stores pipeline schedules in D1. The Cloudflare Cron Trigger is only a scheduler heartbeat; changing a pipeline schedule does not require changing the Worker cron configuration or redeploying the Worker.

Each pipeline has at most one schedule.

### View a schedule

```bash
pulse schedule get <pipeline-id>
```

For example:

```bash
pulse schedule get my-podcast
```

### Update a schedule

`pulse schedule set` creates the schedule when one does not exist and updates the existing schedule otherwise.

```bash
pulse schedule set <pipeline-id> \
  --time HH:MM \
  --timezone <iana-timezone>
```

For example:

```bash
pulse schedule set my-podcast \
  --time 06:30 \
  --timezone America/Chicago
```

The timezone is part of the schedule definition so Pulse can calculate future occurrences correctly across daylight-saving transitions.

The scheduler runs from a shared five-minute Cloudflare Cron heartbeat, so a due schedule is dispatched on the next scheduler tick rather than by a dedicated Cron Trigger for that pipeline.

Verify the updated schedule with:

```bash
pulse schedule get my-podcast
```

### Remove a schedule

```bash
pulse schedule remove <pipeline-id>
```

For example:

```bash
pulse schedule remove my-podcast
```

Removing a schedule stops future scheduled executions. It does not remove the pipeline, its published episodes, or previous run state.

## Run Pulse manually

Run a configured pipeline with:

```bash
pulse run <pipeline-id>
```

For example:

```bash
pulse run my-podcast
```

Manual CLI execution and scheduled execution enter Pulse through different adapters but converge on the same runtime and LangGraph workflow.

A manual run follows:

```text
Pulse CLI
    ↓
RunManager
    ↓
Podcast pipeline runtime
    ↓
LangGraph
```

A scheduled production run follows:

```text
Cloudflare Cron
    ↓
Worker scheduler
    ↓
Cloudflare Workflow
    ↓
RunManager
    ↓
Podcast pipeline runtime
    ↓
LangGraph
```

Running `pulse run` does not create a Cloudflare Workflow instance.

For a fresh manual run, Pulse creates a new logical `run_id`. That identifier is also used as the LangGraph `thread_id` for checkpointing.

Keep the `run_id` when diagnosing or resuming a run.

## Resume a local Pulse run

`pulse run resume` continues a local CLI run from the SQLite checkpointer. It requires the pipeline that owns the run:

```bash
pulse run resume <run-id> --pipeline-id <pipeline-id>
```

For example:

```bash
pulse run resume 725f72a9-6b71-4717-bb1a-4a5dd7d8e242 \
  --pipeline-id my-pipeline
```

The checkpoint file is `PULSE_CHECKPOINT_DATABASE_PATH`. When that variable is unset, local runs use `runtime/pulse-checkpoints.sqlite`.

Resume loads the LangGraph state for that `run_id`. It does not start a new episode, and it does not read production D1 checkpoints.

The local relationship is:

```text
Pulse run_id = LangGraph thread_id
```

For a scheduled Cloudflare execution, the Workflow instance id is the Pulse `run_id` and the LangGraph `thread_id`, and the checkpointer is `WorkerCloudflareD1Saver` on `PULSE_DB`. Recovery of that run is the `run-pipeline` step retry inside `PulsePipelineWorkflow`, which calls `RunManager.run_or_resume`. `pulse run resume` does not load that D1 state.

Pulse resume should not be confused with Cloudflare Workflow instance resume.

```bash
npx wrangler workflows instances resume ...
```

is a Cloudflare operation for a Workflow instance that has been explicitly paused. It is not Pulse's checkpoint-recovery mechanism.

Do not use `pulse run resume` to recover a scheduled production run. Use the Workflow attempt logs and the D1 checkpoint written by that Workflow.

## Observe a deployed installation

### Tail Worker logs

The deployed Worker is `pulse-worker`.

From the repository root:

```bash
npx wrangler@latest tail pulse-worker \
  --config workers/cloudflare/wrangler.jsonc
```

For structured output:

```bash
npx wrangler@latest tail pulse-worker \
  --config workers/cloudflare/wrangler.jsonc \
  --format json
```

`wrangler tail` is useful while reproducing or observing an execution. It is a live stream rather than a historical log store.

Pulse emits structured events at several layers:

```text
Scheduler
    ↓
Cloudflare Workflow attempt
    ↓
Pulse run
    ↓
LangGraph node
```

Use `pipeline_id` to follow work belonging to one configured pipeline and `run_id` to follow one logical execution.

### Scheduler events

The scheduler emits the following lifecycle events:

| Event | Meaning |
| --- | --- |
| `scheduler_tick_started` | A Cron heartbeat entered the scheduler. |
| `scheduler_due_schedules_loaded` | The scheduler finished querying due schedules. |
| `scheduler_no_due_schedules` | The tick found nothing to dispatch. |
| `scheduler_batch_dispatch_started` | Dispatch of a batch of due schedules started. |
| `scheduler_batch_dispatch_completed` | Dispatch of a batch completed. |
| `scheduler_schedule_advanced` | The conditional update matched the expected `next_run_at` and stored the next daily occurrence. |
| `scheduler_schedule_advance_conflict` | The conditional update matched zero rows. The schedule was already advanced, or `next_run_at` changed. |
| `scheduler_tick_completed` | The scheduler tick completed successfully. |
| `scheduler_tick_failed` | The scheduler itself failed. |

Useful scheduler context includes the scheduled tick time, due counts, batch position and size, affected pipeline IDs, and schedule advancement state.

A normal idle heartbeat therefore looks conceptually like:

```text
scheduler_tick_started
scheduler_due_schedules_loaded
scheduler_no_due_schedules
scheduler_tick_completed
```

An idle heartbeat is normal and does not indicate an execution failure.

### Workflow attempt events

Each `PulsePipelineWorkflow` attempt logs:

```text
workflow_attempt_started
```

If the attempt raises an exception:

```text
workflow_attempt_failed
```

Workflow-attempt logs carry the logical `run_id`, `pipeline_id`, and attempt number. Failure events additionally include the exception type and message.

The Cloudflare Workflow step is:

```text
run-pipeline
```

and is configured to retry failures within the Cloudflare Workflow execution envelope.

A retry retains the same Cloudflare Workflow instance ID and therefore the same Pulse `run_id`.

That stable identity is what allows the inner LangGraph execution to load the existing D1 checkpoint instead of blindly starting a second logical run.

### Run lifecycle events

`RunManager` execution is instrumented with three run-level events:

| Event | Meaning |
| --- | --- |
| `run_started` | A fresh or resumed logical run entered the application runtime. |
| `run_completed` | The run reached a successful terminal state. |
| `run_failed` | Execution escaped the runtime with an exception. |

Run logs include `run_id` and `pipeline_id`.

`run_started` records an input summary, including whether the invocation is a new execution or a resume.

`run_completed` includes elapsed time and a result summary. The result identifies the terminal workflow outcome and, where applicable, the episode or no-content reason.

`run_failed` includes elapsed time together with `error_type` and `error_message`.

### Node lifecycle events

Every LangGraph node is wrapped by the node logger.

The node lifecycle events are:

| Event | Meaning |
| --- | --- |
| `node_started` | Node execution began. |
| `node_completed` | Node execution completed successfully. |
| `node_failed` | Node execution raised an exception. |

Node logs carry the current `run_id`, `pipeline_id`, and `node_name`.

Successful completion includes `elapsed_ms` and a compact `result_summary`.

Failures include:

```text
error_type
error_message
```

with the exception traceback emitted separately by the logger.

The current graph includes nodes such as:

```text
retrieve_sources
ingest_signals
process_semantics
post_process_signals
group_signals
plan_episode
generate_script
generate_episode_metadata
produce_audio
publish_episode
commit_signals
complete_without_episode
```

Following one `run_id` through `node_started`, `node_completed`, and `node_failed` events is usually the fastest way to identify where an execution stopped.

## Inspect Cloudflare Workflow instances

The deployed Workflow resource is:

```text
pulse-pipeline
```

### List instances

```bash
npx wrangler@latest workflows instances list pulse-pipeline \
  --config workers/cloudflare/wrangler.jsonc
```

Instances can also be filtered by Cloudflare status:

```bash
npx wrangler@latest workflows instances list pulse-pipeline \
  --status errored \
  --config workers/cloudflare/wrangler.jsonc
```

Cloudflare statuses describe the outer Workflow instance, for example whether it is queued, running, paused, errored, terminated, or complete.

They do not replace Pulse's application-level outcome.

### Inspect the latest instance

```bash
npx wrangler@latest workflows instances describe pulse-pipeline latest \
  --config workers/cloudflare/wrangler.jsonc
```

### Inspect a specific instance

```bash
npx wrangler@latest workflows instances describe pulse-pipeline <instance-id> \
  --config workers/cloudflare/wrangler.jsonc
```

For machine-readable output:

```bash
npx wrangler@latest workflows instances describe pulse-pipeline <instance-id> \
  --config workers/cloudflare/wrangler.jsonc \
  --json
```

`instances describe` exposes the state of the outer Workflow execution, including step attempts, retries, errors, timing, and step output.

Pulse currently executes the pipeline inside one Cloudflare Workflow step:

```text
run-pipeline
```

The individual LangGraph nodes are therefore visible through Pulse logs and checkpoints, not as separate Cloudflare Workflow steps.

## Inspect the Workflow result

A successful `run-pipeline` step returns a compact Pulse result containing:

```json
{
  "run_id": "...",
  "pipeline_id": "...",
  "episode_id": "...",
  "workflow_outcome": "published",
  "no_content_reason": null
}
```

A successful run that intentionally produced no episode instead resembles:

```json
{
  "run_id": "...",
  "pipeline_id": "...",
  "episode_id": null,
  "workflow_outcome": "no_content",
  "no_content_reason": "no_unseen_signals"
}
```

`workflow_outcome` currently serializes the enum value rather than its uppercase Python member name.

The successful outcomes are:

```text
published
no_content
```

Failures are not represented as a third workflow outcome. Unexpected failures propagate as exceptions and appear as failed Pulse runs and, after Cloudflare retries are exhausted, errored Workflow instances.

## Understand run outcomes

There are three operationally important results.

### Episode published

A normal episode-producing run finishes with:

```text
workflow_outcome = published
```

and an `episode_id`.

The graph reaches publication before committing the processed signals to the durable signal history:

```text
publish_episode
    ↓
commit_signals
    ↓
published
```

This ordering is intentional: signals are not considered consumed merely because an earlier stage of generation succeeded.

After a published result, verify the public artifacts before considering the operation fully checked.

### Successful no-content run

A run can complete successfully without creating an episode:

```text
workflow_outcome = no_content
```

This is not a failure.

The current no-content reasons are:

```text
no_unseen_signals
no_semantically_unique_signals
no_processed_signals
no_themed_clusters
```

These correspond to intentional early exits where the current source material cannot produce a valid episode.

A Cloudflare Workflow instance for such a run should still finish successfully.

### Failed run

A failed run emits:

```text
run_failed
```

or:

```text
node_failed
```

and the Cloudflare Workflow attempt may emit:

```text
workflow_attempt_failed
```

Cloudflare may retry the outer `run-pipeline` step automatically.

Because the retry uses the same logical `run_id`, Pulse can recover from the persisted LangGraph checkpoint rather than treating the retry as an unrelated run.

If Cloudflare exhausts its attempts, the Workflow instance becomes errored.

## Verify a published episode

Do not use Workflow completion alone as proof that the public podcast artifacts are reachable.

Verify the RSS document and the URLs referenced by it.

### Verify RSS

Pulse publishes one RSS feed per show:

```text
https://<podcast-host>/shows/<show-id>/rss.xml
```

Check that it is publicly reachable:

```bash
curl -I https://<podcast-host>/shows/<show-id>/rss.xml
```

Then inspect it:

```bash
curl https://<podcast-host>/shows/<show-id>/rss.xml
```

Confirm that the newest item contains the expected episode metadata and enclosure.

### Verify audio

Take the enclosure URL from the RSS item and verify it directly:

```bash
curl -I "<audio-url>"
```

The resource should be publicly reachable and served as audio content.

The enclosure URL in RSS should match the audio URL produced for the published episode.

### Verify artwork

Take the show artwork URL from the RSS document and verify it directly:

```bash
curl -I "<artwork-url>"
```

The artwork should also be publicly reachable without Cloudflare API credentials.

These public resources may use an R2 development domain or a configured custom podcast domain depending on the deployment.

## Recover from common operational failures

### A scheduled episode did not start

First inspect the configured schedule:

```bash
pulse schedule get <pipeline-id>
```

Then tail the Worker and look for the scheduler lifecycle:

```text
scheduler_tick_started
scheduler_due_schedules_loaded
```

If the schedule was due, continue through the batch dispatch and schedule-advancement events.

Remember that the shared scheduler heartbeat runs every five minutes. A pipeline scheduled between heartbeat boundaries is dispatched on the next scheduler tick.

If the scheduler is not running at all, verify the Worker deployment and Cron configuration in [Deployment](deployment.md).

### The Workflow instance errored

Inspect the instance:

```bash
npx wrangler@latest workflows instances describe pulse-pipeline <instance-id> \
  --config workers/cloudflare/wrangler.jsonc
```

Check the `run-pipeline` attempts and the final exception.

Then correlate the same identifier in Pulse logs. For scheduled executions:

```text
Cloudflare Workflow instance ID = Pulse run_id = LangGraph thread_id
```

If the logical run has a usable D1 checkpoint, the next `run-pipeline` attempt resumes it through `RunManager.run_or_resume`. That is separate from a local CLI resume.

### A Pulse node failed partway through the graph

Find the final:

```text
node_failed
```

event for the run and inspect its `node_name`, `error_type`, and `error_message`.

The persisted checkpoint records completed graph progress. Resuming the logical run allows LangGraph to continue from its persisted state rather than reconstructing the run from scratch.

For checkpoint-specific investigation, see [Troubleshooting](troubleshooting.md).

### The run completed with `no_content`

No recovery is normally required.

Inspect `no_content_reason` to understand which successful early-exit condition was reached.

If the result was unexpected, investigate the relevant upstream stage — retrieval, exact deduplication, semantic deduplication, post-processing, or grouping — rather than treating `no_content` itself as an infrastructure failure.

### Cloudflare completed successfully but the expected episode is missing

Inspect the `run-pipeline` result first.

A complete Cloudflare Workflow can represent either:

```text
workflow_outcome = published
```

or:

```text
workflow_outcome = no_content
```

If the result is `no_content`, no episode should exist.

If the result is `published`, verify RSS, audio, and artwork directly and inspect the `publish_episode` and `commit_signals` node logs.

Do not assume that rerunning publication is harmless. Pulse should not be described operationally as providing exactly-once external side effects.

Investigate the existing run before starting a replacement execution.

### RSS exists but audio or artwork is inaccessible

Verify the affected URL directly with `curl`.

If RSS generation succeeded but a referenced R2 object or public URL is unavailable, inspect the publishing configuration, R2 object state, and public-domain configuration.

See [Deployment](deployment.md) for R2 public access and domain setup, and [Troubleshooting](troubleshooting.md) for deeper publishing failures.

## Operational model

When diagnosing Pulse, keep the execution layers separate:

```text
Schedule
    determines when work is due

Cloudflare Cron + scheduler
    discovers and dispatches due work

Cloudflare Workflow
    provides durable outer execution and retries

RunManager
    owns one logical Pulse run

LangGraph + D1 checkpoints
    provide workflow state and resume

Publisher + R2
    produce public podcast artifacts
```

A problem at one layer does not necessarily imply failure at another.

Start with the observable outcome, identify the relevant `run_id`, and move inward from the Cloudflare Workflow instance to the Pulse run and then to the individual LangGraph node.