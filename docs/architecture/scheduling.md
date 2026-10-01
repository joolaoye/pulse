# Scheduling

Pulse separates **when a pipeline should run** from **how that pipeline executes**.

Pipeline-specific schedules are persisted as application state in D1. Cloudflare owns only one recurring Cron Trigger that wakes the scheduler periodically.

The production path is:

```text
Cloudflare Cron heartbeat
        ↓
Worker scheduled()
        ↓
find due enabled schedules
        ↓
dispatch Cloudflare Workflow instances
        ↓
compare-and-swap each schedule to its next occurrence
        ↓

each Workflow
        ↓
RunManager
        ↓
LangGraph
```

The scheduler never executes retrieval, generation, audio production, or publishing itself.

Its responsibility ends once a durable Pulse Workflow has been started for the scheduled occurrence.

---

## Overview

![Pulse scheduled execution lifecycle](../assets/pulse-lifecycle-architecture.svg)

Pulse has two different kinds of time configuration:

```text
Cloudflare Cron Trigger
    → when the scheduler wakes up

PodcastPipelineSchedule
    → when a particular pipeline should run
```

These are deliberately independent.

For V1, the deployed Worker has one scheduler heartbeat:

```text
*/5 * * * *
```

Every five minutes, Cloudflare wakes the same scheduler regardless of how many podcast pipelines are configured.

The scheduler then queries D1 to determine which pipelines are actually due.

---

## Why one permanent Cron heartbeat

Pulse does not create a Cloudflare Cron Trigger for every pipeline.

Instead:

```text
one Cloudflare Cron
        ↓
many persisted Pulse schedules
```

This avoids making infrastructure deployment part of normal podcast configuration.

With per-pipeline Cloudflare crons, changing:

```text
06:30 → 07:00
```

would require modifying Wrangler configuration and redeploying the Worker.

With Pulse's architecture, the change is only:

```text
update one D1 schedule row
```

The deployed scheduler continues waking at the same five-minute heartbeat and automatically observes the new configuration.

This is why:

```bash
pulse schedule set <pipeline-id>
```

does not require a subsequent:

```bash
pulse deploy
```

---

## V1 schedule model

V1 intentionally keeps the user-facing recurrence model small:

> One pipeline may have one daily schedule.

The persisted domain model is `PodcastPipelineSchedule`.

Conceptually:

```text
PodcastPipelineSchedule
├── pipeline_id
├── local_time
├── timezone
├── next_run_at
└── last_dispatched_at
```

The fields serve different purposes.

| Field | Meaning |
| --- | --- |
| `pipeline_id` | Pipeline whose execution is controlled by the schedule |
| `local_time` | Desired daily wall-clock time |
| `timezone` | IANA timezone used to interpret that local time |
| `next_run_at` | Next concrete scheduled occurrence, persisted in UTC |
| `last_dispatched_at` | UTC time of the scheduler heartbeat that most recently dispatched the schedule |

There is one persisted schedule row per pipeline.

`last_dispatched_at` can be empty before the first successful dispatch.

The persisted schedule is application configuration. It is not a Cloudflare deployment object.

---

## Local time and timezone

The schedule describes a human-facing local clock time rather than forcing users to calculate UTC offsets themselves.

For example:

```bash
pulse schedule set my-pipeline \
  --time 06:30 \
  --timezone America/Chicago
```

means:

> Run this pipeline each local calendar day at 06:30 in `America/Chicago`.

Pulse stores both:

```text
local_time = 06:30
timezone   = America/Chicago
```

rather than converting the schedule permanently into a fixed UTC hour.

That distinction matters because UTC offsets can change during daylight-saving transitions.

---

## UTC execution state

Human configuration is local.

Scheduler state is UTC.

The important boundary is:

```text
local_time + timezone
        ↓
timezone-aware schedule calculation
        ↓
next_run_at in UTC
```

`next_run_at` is what the scheduler compares against its current cutoff.

The Worker therefore does not depend on:

```text
developer machine timezone
Worker process timezone
server locale
```

for dispatch decisions.

---

## `next_daily_occurrence`

Pulse centralizes daily schedule calculation in:

```text
next_daily_occurrence(
    local_time,
    timezone_name,
    after,
)
```

Its contract is:

```text
local wall-clock time
+
IANA timezone
+
timezone-aware cutoff
        ↓
first matching occurrence strictly after cutoff
        ↓
UTC datetime
```

The result always satisfies:

```text
candidate_utc > after_utc
```

not:

```text
candidate_utc >= after_utc
```

This strict boundary is important when advancing schedules after dispatch.

The calculation advances by **local calendar days**, not by adding a fixed 24-hour UTC duration.

That preserves the requested local wall-clock time across timezone offset changes.

The current implementation uses Python's standard `zoneinfo` timezone support rather than introducing a separate scheduling framework.

---

## Schedule-time validation

V1 daily schedules use minute precision.

A configured `local_time` is a wall-clock value and therefore must not already contain timezone information.

Conceptually:

```text
06:30
    valid

06:30:15
    invalid for V1

06:30 with tzinfo attached
    invalid
```

The timezone is supplied separately through the schedule's IANA timezone field.

The cutoff passed to schedule calculation must itself be timezone-aware.

Unknown timezone names are rejected rather than silently falling back to UTC or the host machine's timezone.

---

## Daylight-saving behavior

Because schedules are defined in local wall-clock time, DST transitions must have deterministic behavior.

### Fall back

During a fall-back transition, some local times occur twice.

For example:

```text
01:30
```

may exist once before the offset change and once after it.

Pulse uses the **first occurrence** of an ambiguous local time.

Conceptually:

```text
daily schedule = 01:30

first 01:30
    → scheduled occurrence

second 01:30
    → not another occurrence
```

This prevents one daily schedule from producing two runs simply because the clock repeated an hour.

After that day's occurrence has passed, the next calculation proceeds to the next local calendar day.

### Spring forward

During a spring-forward transition, some wall-clock times do not exist.

For example:

```text
02:30
```

may fall inside the skipped interval.

The current timezone calculation normalizes that nonexistent local time forward through the transition to the corresponding valid instant rather than creating an invalid datetime or an extra occurrence.

The important V1 rule is:

> A timezone transition must not create duplicate daily runs, and daily scheduling remains anchored to local calendar semantics rather than fixed 24-hour UTC intervals.

---

## Cron cutoff

When Cloudflare invokes the Worker's `scheduled()` handler, Pulse does not use an arbitrary call to the process clock as the scheduling cutoff.

It uses Cloudflare's scheduled event timestamp:

```text
controller.scheduledTime
```

and converts that millisecond timestamp into an aware UTC datetime:

```text
scheduled_at
```

Conceptually:

```text
Cloudflare scheduled event
        ↓
controller.scheduledTime
        ↓
UTC scheduled_at
        ↓
list_due(cutoff=scheduled_at)
```

Using the event's scheduled timestamp gives one deterministic cutoff to the entire scheduler invocation.

---

## Due-schedule selection

The scheduler asks the application layer for schedules whose persisted occurrence is due at the current cutoff.

Conceptually:

```text
next_run_at <= cutoff
        +
pipeline.enabled = true
        ↓
due schedule
```

The schedule repository joins persisted schedule state with its corresponding `PodcastPipeline`.

The relevant selection behaves like:

```sql
FROM podcast_pipeline_schedule AS schedule
JOIN podcast_pipeline AS pipeline
  ON pipeline.pipeline_id = schedule.pipeline_id
WHERE schedule.next_run_at <= ?
  AND pipeline.enabled = 1
```

The exact pipeline `enabled` flag is the source of truth.

There is no second scheduler-specific enabled flag.

---

## Enabled and disabled pipelines

A schedule does not run independently of its pipeline.

The rule is:

```text
schedule due
+
pipeline enabled
    → dispatch

schedule due
+
pipeline disabled
    → do not dispatch
```

Disabled schedules are not advanced merely because time passes.

Their persisted `next_run_at` remains unchanged while the pipeline is disabled.

This is intentional.

It means disabling a pipeline pauses execution without destroying or continuously rewriting its schedule.

---

## Re-enabling an overdue pipeline

A consequence of freezing disabled schedules is that a pipeline can be re-enabled with a `next_run_at` that is already in the past.

Pulse does not replay every missed day.

Instead:

```text
pipeline disabled for several occurrences
        ↓
next_run_at remains old
        ↓
pipeline re-enabled
        ↓
next scheduler heartbeat sees it as overdue
        ↓
dispatch once
        ↓
advance directly to first future daily occurrence
```

This gives Pulse **missed-run coalescing**.

A long outage or disabled period therefore produces at most one catch-up dispatch when the schedule becomes eligible again.

---

## Missed-run coalescing

The same behavior applies when the scheduler itself has not run for several expected occurrences.

Suppose a daily schedule was due on Monday, but the next scheduler cutoff is Thursday.

Pulse does not produce:

```text
Monday run
Tuesday run
Wednesday run
Thursday run
```

in rapid succession.

Instead:

```text
old next_run_at
    → represents one overdue occurrence

scheduler dispatches it once
    ↓
advance using Thursday's scheduler cutoff
    ↓
next_run_at becomes the first daily occurrence after Thursday
```

For a normal daily schedule, that would usually mean Friday.

The scheduler therefore coalesces missed history into one logical catch-up invocation.

---

## Scheduled occurrence identity

Two timestamps are important during dispatch:

```text
schedule.next_run_at
    → which scheduled occurrence is being dispatched

scheduled_at
    → when this scheduler heartbeat is processing it
```

They are not interchangeable.

Consider an overdue schedule:

```text
next_run_at
    Monday 06:30

scheduled_at
    Thursday 12:00
```

The Workflow must still have the identity of the **Monday occurrence**, because that is the persisted occurrence the scheduler observed.

The Thursday cutoff is used when advancing the schedule afterward.

---

## Deterministic Workflow IDs

Every scheduled occurrence receives a deterministic Cloudflare Workflow instance ID.

The helper is:

```text
build_scheduled_workflow_id(
    pipeline_id,
    scheduled_for,
)
```

where:

```text
scheduled_for = schedule.next_run_at
```

The identity is therefore derived from:

```text
pipeline_id
+
persisted scheduled occurrence
```

and not from the time the Worker happens to process the Cron event.

The resulting ID uses a stable SHA-256-based form:

```text
scheduled-<digest>
```

The same:

```text
pipeline
+
scheduled occurrence
```

always produces the same Workflow ID.

A different daily occurrence produces a different Workflow ID.

This gives the scheduler a durable idempotency key without relying on Worker memory.

---

## Why the Workflow ID uses `next_run_at`

Using the persisted occurrence provides the desired identity rule:

```text
same pipeline
+
same scheduled occurrence
=
same logical Workflow
```

If an overlapping Cron invocation sees the same due row before it has been advanced, it computes the same Workflow ID.

It must not create a second logical Pulse run for that occurrence.

By contrast, using only:

```text
pipeline_id
```

would prevent future scheduled runs from having distinct identities.

Using the scheduler heartbeat time would also be incorrect because two different heartbeat invocations could process the same overdue occurrence.

---

## Workflow dispatch

For each due schedule, the Worker builds a Cloudflare Workflow instance with:

```text
id
    deterministic scheduled Workflow ID

params
    pipeline_id
```

Due instances are dispatched through:

```text
PULSE_PIPELINE_WORKFLOW.create_batch(...)
```

The current Worker batches at most 100 Workflow instances into one `create_batch` call.

Conceptually:

```text
list_due(cutoff)
    ↓
due schedules
    ↓
build deterministic Workflow IDs
    ↓
create_batch(...)
```

Only after Cloudflare accepts the dispatch does Pulse advance those schedule occurrences.

---

## Schedule advancement

Dispatch and schedule advancement are separate steps.

For each successfully dispatched schedule:

```text
advance_occurrence(
    schedule=schedule,
    dispatched_at=scheduled_at,
)
```

computes:

```text
next_run_at =
    first daily occurrence
    strictly after dispatched_at
```

and records:

```text
last_dispatched_at = dispatched_at
```

This is what creates missed-run coalescing.

The algorithm advances from the scheduler cutoff, not merely:

```text
old next_run_at + 1 day
```

Otherwise a heavily overdue schedule would remain overdue and replay historical occurrences one by one.

---

## Compare-and-swap advancement

Schedule advancement uses a conditional D1 update.

Conceptually:

```sql
UPDATE podcast_pipeline_schedule
SET
    next_run_at = <new value>,
    last_dispatched_at = <dispatch cutoff>
WHERE pipeline_id = <pipeline>
  AND next_run_at = <expected old occurrence>
```

The persisted old `next_run_at` is the compare-and-swap value.

This protects schedule configuration from stale scheduler invocations.

For example:

```text
scheduler reads 06:30 schedule
        ↓
user changes schedule to 08:00
        ↓
old scheduler finishes dispatch
        ↓
CAS expects old next_run_at
        ↓
zero rows match
```

The scheduler does **not** overwrite the newer 08:00 configuration.

`advance_occurrence` therefore returns whether the conditional advancement succeeded.

A failed CAS is not automatically a scheduler failure.

It means the schedule changed, or another invocation already advanced that occurrence.

---

## Duplicate prevention

V1 uses two complementary mechanisms.

### Deterministic Workflow identity

```text
pipeline_id + scheduled next_run_at
        ↓
stable Workflow ID
```

protects against launching two logical Workflow instances for the same scheduled occurrence.

### D1 compare-and-swap advancement

```text
expected persisted next_run_at
        ↓
conditional UPDATE
```

prevents overlapping or stale scheduler invocations from incorrectly advancing newer schedule state.

Together they handle the important race:

```text
heartbeat A reads occurrence
heartbeat B reads same occurrence
        ↓
both derive same Workflow identity
        ↓
at most one logical Workflow occurrence
        ↓
one advancement may succeed
other CAS becomes a harmless no-op
```

Pulse does not use an in-memory scheduler lock.

Worker invocations are ephemeral, so process-local locking would not provide the required durability.

---

## Scheduler advancement does not wait for episode success

The scheduler's job is to hand an occurrence to the durable Workflow layer.

Therefore the schedule is advanced after the Cloudflare Workflow dispatch is accepted.

It does **not** wait for:

```text
retrieval
generation
audio synthesis
publication
```

to finish.

After dispatch:

```text
schedule occurrence
    → considered handed off

Workflow instance
    → owns completion / retry
```

If the podcast run later fails, the failure belongs to that Workflow instance.

The scheduler does not create a replacement occurrence merely because the episode has not yet succeeded.

---

## Scheduler, Workflow, RunManager, and LangGraph

These layers intentionally own different lifecycles.

| Layer | Owns |
| --- | --- |
| Cloudflare Cron | Periodically waking the Worker |
| Worker scheduler | Due selection, occurrence identity, Workflow dispatch, schedule advancement |
| Cloudflare Workflow | Durable execution envelope for one scheduled occurrence |
| `RunManager` | One logical Pulse application run |
| LangGraph | Episode-stage orchestration, workflow state, checkpointing, and resume |

The complete path is:

```text
Cron heartbeat
    ↓
Worker scheduler
    ↓
Cloudflare Workflow
    ↓
RunManager
    ↓
PodcastPipelineRuntimeFactory
    ↓
LangGraph
```

The scheduler never directly constructs generation services or invokes LangGraph nodes.

The Cloudflare Workflow likewise does not contain another implementation of the episode pipeline.

All invocation paths converge on the same application runtime.

---

## Scheduled run identity

The Cloudflare Workflow instance has a stable instance identity.

For scheduled runs, that identity becomes the logical Pulse `run_id`.

LangGraph uses the same logical identity as its checkpoint `thread_id`.

Conceptually:

```text
scheduled occurrence
    ↓
deterministic Workflow instance ID
    ↓
Workflow instance
    ↓
run_id
    ↓
LangGraph thread_id
```

This aligns the outer durable execution identity with Pulse's internal checkpoint identity.

A new scheduled occurrence gets a new Workflow ID and therefore a new logical Pulse run.

A retry of an existing Workflow does not.

---

## Retry and resume behavior

Retries must preserve logical run identity.

The intended lifecycle is:

```text
scheduled occurrence
        ↓
one Cloudflare Workflow instance
        ↓
one logical run_id
        ↓
one LangGraph thread_id
```

If execution fails after LangGraph has checkpointed completed work:

```text
same Workflow instance retries
        ↓
same run_id
        ↓
same LangGraph thread_id
        ↓
restore checkpoint
        ↓
continue the same logical run
```

Pulse must not turn a Cloudflare retry into:

```text
new Workflow retry
    ↓
new random run_id
    ↓
new episode
```

That would duplicate paid generation work and break resume semantics.

---

## Workflow success and failure

Scheduled execution distinguishes business outcomes from execution failures.

Successful Pulse outcomes include:

```text
PUBLISHED
NO_CONTENT
```

`NO_CONTENT` is a valid completed run. It must not cause the scheduler or Cloudflare Workflow to repeatedly retry the occurrence.

Provider failures, infrastructure failures, or unhandled application exceptions remain execution failures.

Those are retried or resumed within the durable Workflow / LangGraph execution lifecycle using the same logical run identity.

---

## Schedule changes

Schedule configuration lives entirely in D1.

Commands such as:

```bash
pulse schedule set <pipeline-id>
pulse schedule remove <pipeline-id>
```

modify persisted application state.

They do not change:

```text
Worker code
Wrangler configuration
Cloudflare Workflow definition
Cron Trigger
```

The fixed Cron heartbeat continues to wake the scheduler, and the next invocation observes the latest persisted schedule state.

This is why schedule configuration can change independently of application deployment.

---

## Architectural invariants

The V1 scheduler preserves several important rules:

```text
one deployed Cron heartbeat
    → many persisted pipeline schedules

local wall-clock configuration
    → UTC next_run_at

due + enabled
    → eligible for dispatch

due + disabled
    → frozen

multiple missed occurrences
    → one coalesced dispatch

pipeline + persisted occurrence
    → deterministic Workflow identity

Workflow accepted
    → schedule advances

stale advancement
    → CAS no-op, never overwrite newer configuration

Workflow retry
    → same run_id

LangGraph resume
    → same thread_id
```

The central ownership rule is:

> The scheduler decides **when to start a logical run**. Cloudflare Workflow keeps that invocation durable. `RunManager` owns the logical Pulse run. LangGraph owns the episode workflow and its resumable state.

---

## Related documentation

- [System architecture](../architecture.md) — control-plane, execution, and episode-pipeline boundaries.
- [Configuration](../configuration.md) — persisted pipeline and schedule configuration.
- [Deployment](../deployment.md) — Worker, Workflow, D1, and Cron deployment.
- [Operations](../operations.md) — inspecting schedules, Workflows, and deployed runs.
- [Troubleshooting](../troubleshooting.md) — scheduler, Worker, and Workflow failures.