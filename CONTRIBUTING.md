# Contributing to Pulse

Thanks for contributing to Pulse.

This document is the contributor entrypoint. It covers the expected development workflow, architectural boundaries, testing expectations, and pull-request checklist.

For deeper development details, see [Development](docs/internal/development.md). For release procedures, see [Release](docs/internal/release.md).

## Before you start

Pulse is a Python application with a Cloudflare production runtime.

Its major source areas are:

```text
src/pulse/
├── agents/
├── application/
│   └── orchestration/
├── cli/
├── infrastructure/
├── services/
└── types/
```

The Cloudflare runtime adapter lives under:

```text
workers/cloudflare/
```

Tests are organized under:

```text
tests/
├── unit/
├── integration/
└── e2e/
```

Before making a structural change, read [Development](docs/internal/development.md) and the relevant architecture documentation under `docs/architecture/`.

## Set up the repository

Pulse uses `uv` for Python dependency management.

On macOS or Linux:

```bash
bash bootstrap.sh
```

On Windows PowerShell:

```powershell
.\bootstrap.ps1
```

Then verify the environment:

```bash
uv run pulse --help
uv run pytest --help
```

You can also synchronize the Python environment directly:

```bash
uv sync
```

## Development workflow

A typical contribution should follow:

```text
understand the owning layer
        ↓
make the smallest coherent change
        ↓
add or update focused tests
        ↓
run affected tests
        ↓
run broader tests where required
        ↓
update documentation if behavior changed
        ↓
review the final diff
```

Avoid combining unrelated refactors, formatting changes, and feature work in the same change unless they genuinely belong together.

## Respect the architecture

Pulse separates reasoning, capabilities, orchestration, infrastructure, and external adapters.

At a high level:

```text
types
     ↑
agents / services
     ↑
application, including orchestration
     ↑
cli / workers
```

`infrastructure/` provides concrete external-system implementations that are wired into the application through composition.

These boundaries are intentional.

### `types/`

`types/` contains shared typed contracts and canonical data representations.

Before introducing a new type, check whether the concept already has a current representation.

Do not recreate legacy DTOs from older Pulse architectures.

### `agents/`

`agents/` contains focused LLM-backed reasoning or generation capabilities.

Agents should:

- have narrow responsibilities;
- use typed inputs and outputs;
- keep prompts and model configuration close to the agent;
- receive their LLM/provider dependencies through composition.

Do not construct production providers directly inside an agent.

### `services/`

`services/` contains reusable Pulse capabilities.

A service should not know:

- which LangGraph node invokes it;
- which node runs next;
- whether execution came from the CLI or Cloudflare;
- how the complete application is assembled.

Those concerns belong to `application/orchestration/` or the rest of the application layer.

### `application/orchestration/`

`application/orchestration/` owns the LangGraph episode workflow.

This includes:

- workflow state;
- LangGraph nodes;
- edges and routing;
- terminal conditions;
- graph construction;
- the local SQLite checkpointer.

Changes to graph order, state, routing, or terminal behavior belong here rather than in a service.

### `infrastructure/`

`infrastructure/` contains concrete provider and persistence implementations.

Examples include integrations with:

- Cloudflare D1;
- Cloudflare R2;
- Cloudflare Vectorize;
- X;
- Anthropic;
- Voyage;
- ElevenLabs.

Keep provider-specific response types and implementation details from leaking unnecessarily into services or orchestration nodes.

### `application/`

`application/` owns composition and application use cases.

It is responsible for wiring together:

```text
types
agents
services
infrastructure
orchestration
```

into runnable Pulse behavior.

Runtime construction, deployment, configuration, run management, and similar application-level coordination belong here.

### `cli/` and `workers/`

These are adapters.

The CLI and Cloudflare Worker should translate external execution into application calls rather than reimplementing application behavior.

If logic is useful from both the CLI and Worker, it should almost certainly live below those adapters.

## Preserve the current workflow semantics

The current podcast pipeline is approximately:

```text
retrieve_sources
    ↓
ingest_signals
    ↓
process_semantics
    ↓
post_process_signals
    ↓
group_signals
    ↓
plan_episode
    ↓
generate_script
    ↓
generate_episode_metadata
    ↓
produce_audio
    ↓
publish_episode
    ↓
commit_signals
```

Successful early exits terminate through:

```text
complete_without_episode
    ↓
END
```

That path does not call `commit_signals` and does not write signal history.

Some ordering decisions are operationally significant.

In particular:

```text
publish_episode
    ↓
commit_signals
```

is intentional.

Signals should not be permanently marked consumed before the episode has been successfully published.

Do not reorder workflow stages without considering checkpoint, retry, resume, and external side-effect behavior.

## Checkpoint and resume behavior

Pulse uses the logical:

```text
run_id
```

as the LangGraph:

```text
thread_id
```

for checkpointing.

A workflow change must therefore be reviewed not only for fresh execution, but also for resumed execution.

When modifying a node, ask:

- what state does it require?
- what state does it produce?
- what has already been checkpointed when it runs?
- what happens if it fails?
- what happens when execution resumes?
- is repeating the operation safe?
- does it perform an external side effect?

Do not assume checkpointing makes external operations exactly-once.

## Adding or changing a service

When changing a service:

1. identify the canonical input/output types;
2. keep provider-specific implementation behind `infrastructure/`;
3. implement the service behavior;
4. add focused unit tests;
5. update application composition if dependencies changed;
6. update `application/orchestration/` if state or routing changed;
7. run the appropriate broader tests.

A service should remain independently testable wherever practical.

## Adding or changing an agent

When modifying an agent, review together:

- typed input;
- typed output;
- prompt;
- examples;
- model selection;
- temperature/token settings;
- downstream consumers;
- tests.

Avoid generic exported constants that can collide across agent modules.

A prompt or structured-output change may be an application-contract change even when no Python function signature changes.

## Adding or changing infrastructure

Infrastructure changes should preserve their application-facing contracts where possible.

When modifying a repository or provider adapter:

- keep provider-specific behavior contained;
- add focused tests;
- add integration coverage when real persistence semantics matter;
- consider retry behavior;
- consider idempotency;
- verify Cloudflare Worker compatibility if the code runs there.

Changes to D1 persistence should also be reviewed against checkpoint and resume behavior.

## Cloudflare Worker compatibility

Pulse runs in Cloudflare's Python Worker environment.

That environment is not identical to local CPython.

A dependency that works locally may still fail because of:

- Pyodide compatibility;
- unsupported native extensions;
- transitive imports;
- missing runtime behavior;
- bundle-size growth.

Do not assume local test success proves Worker compatibility.

The Worker build is assembled and validated by the tested Python deployment implementation.

Generated directories such as:

```text
workers/cloudflare/python_modules/
```

must not be edited manually.

If Worker assembly is incorrect, fix the implementation that creates it.

## Compatibility stubs

Pulse contains narrowly scoped compatibility stubs for dependencies that expect behavior unavailable directly in the Cloudflare runtime.

Do not add a new stub merely to silence an import failure.

First determine whether:

1. the dependency is actually required;
2. the import can be avoided;
3. the dependency is otherwise compatible with Pyodide;
4. the behavior can be safely emulated.

Compatibility stubs should remain minimal and deterministic.

## Testing

Every behavioral change should include appropriate automated coverage.

### Unit tests

Use unit tests for isolated behavior such as:

- services;
- agents;
- workflow nodes;
- routing;
- deployment components;
- logging;
- pure infrastructure behavior.

Run focused tests while developing:

```bash
uv run pytest <path-to-test>
```

### Integration tests

Use integration tests where correctness depends on interaction between real components, particularly persistence or repository semantics.

### End-to-end tests

Use end-to-end tests when a change crosses enough boundaries that isolated tests no longer prove the complete behavior.

Run the complete suite before submitting a significant change:

```bash
uv run pytest
```

Do not weaken or skip a failing test merely to make the suite green unless the test itself is incorrect.

## Build-sensitive changes

Changes involving:

- dependencies;
- deployment;
- Worker imports;
- compatibility stubs;
- package structure;
- application composition

should also exercise the Worker build path.

Build a fresh wheel with:

```bash
uv build --wheel
```

Do not rely on stale `dist/` output or an existing `python_modules` directory when validating a build-sensitive change.

See [Development](docs/internal/development.md) for the full Worker build and bundle-validation process.

## Documentation changes

Update documentation when a contribution changes:

- CLI commands;
- configuration;
- public behavior;
- deployment requirements;
- operational procedures;
- workflow semantics;
- architecture;
- contributor workflow.

Use the implementation as the source of truth.

Do not document planned behavior as though it already exists.

Architecture diagrams are maintained separately in `pulse-diagrams`; Pulse documentation consumes their exported assets.

## Generated files and secrets

Do not commit generated or machine-specific state.

Examples include:

```text
.venv/
dist/
workers/cloudflare/python_modules/
wrangler.jsonc
```

or temporary Worker archives.

Never commit:

- API tokens;
- provider keys;
- `.env` secrets;
- Cloudflare credentials;
- private test data;
- credentials embedded in documentation or fixtures.

Before submitting a change, inspect:

```bash
git status
git diff
git diff --cached
```

## Code style

Prefer code that makes architectural ownership obvious.

### Keep functions and classes focused

Do not make one component responsible for several unrelated pipeline stages.

### Prefer explicit dependency injection

Avoid hidden global clients or service locators.

### Reuse current types

Search `types/` before creating another representation of an existing concept.

### Avoid unnecessary package exports

Be cautious with `__init__.py` barrel imports.

They can create name collisions and may pull unnecessary or unsupported dependencies into the Cloudflare runtime.

### Keep adapters thin

CLI commands and Worker handlers should delegate rather than implement application behavior.

### Prefer structured logs

Use the existing scheduler, Workflow, run, and node logging conventions for lifecycle events.

### Optimize for readability

Prefer straightforward code over unnecessary abstraction.

New abstractions should represent a stable responsibility or boundary rather than merely reducing a few repeated lines.

## Pull requests

A pull request should explain:

- what changed;
- why the change is needed;
- which architectural layer owns the change;
- important implementation decisions;
- how the change was tested;
- whether deployment or operational behavior changed.

For workflow changes, also explain any effect on:

- state;
- routing;
- checkpointing;
- resume;
- external side effects.

For deployment changes, explain any effect on:

- Worker assembly;
- dependencies;
- Wrangler configuration;
- secrets;
- Cloudflare resources;
- bundle size.

Keep pull requests focused enough that reviewers can reason about the affected boundaries.

## Pull-request checklist

Before requesting review:

- [ ] The change belongs to the correct architectural layer.
- [ ] Current `types/` are reused where appropriate.
- [ ] Services do not contain workflow or adapter logic.
- [ ] Provider-specific behavior remains behind `infrastructure/`.
- [ ] CLI and Worker entrypoints remain thin.
- [ ] Workflow changes account for checkpoint and resume behavior.
- [ ] External side effects have been considered for retry safety.
- [ ] Focused tests were added or updated.
- [ ] Relevant integration or end-to-end tests pass.
- [ ] The full test suite passes for significant changes.
- [ ] Worker-sensitive changes have been build-validated.
- [ ] Documentation was updated where behavior changed.
- [ ] No generated files or secrets are included.
- [ ] `git diff` contains only intentional changes.
- [ ] `git status` is understood and clean before finalizing the contribution.

## Releases

Contributors generally do not need to perform the full production release process for every change.

Maintainers preparing a release should follow:

[Release](docs/internal/release.md)

That process includes:

```text
full tests
    ↓
fresh build
    ↓
clean deployment
    ↓
scheduled smoke run
    ↓
RSS / audio / artwork verification
    ↓
Spotify verification
    ↓
version + tag
```

## Principle

A good Pulse contribution should preserve one core property:

> The same application should remain understandable, testable, runnable locally, resumable from checkpoints, and deployable through Cloudflare without duplicating the product across environments.

When a change respects the boundaries between `types`, `agents`, `services`, `infrastructure`, `application/orchestration`, the rest of `application`, and the external adapters, that property is much easier to maintain.