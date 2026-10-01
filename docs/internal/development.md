# Development

This guide covers contributor setup and the development conventions used across Pulse.

It focuses on the repository structure, local environment, architectural boundaries, Cloudflare Worker compatibility, build tooling, and the safest way to change services, agents, workflows, and infrastructure.

For production deployment, see [Deployment](../deployment.md). For operating a deployed installation, see [Operations](../operations.md).

## Repository layout

Pulse is organized around explicit application, domain, infrastructure, and adapter boundaries.

At a high level:

```text
pulse/
├── src/
│   └── pulse/
│       ├── agents/
│       ├── application/
│       │   └── orchestration/
│       ├── cli/
│       ├── infrastructure/
│       ├── services/
│       └── types/
├── workers/
│   └── cloudflare/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── migrations/
├── docs/
├── pyproject.toml
├── uv.lock
├── package.json
├── package-lock.json
├── bootstrap.sh
└── bootstrap.ps1
```

Generated deployment artifacts are not source files and should remain ignored by Git.

### `agents/`

`agents/` contains LLM-backed capabilities.

An agent normally owns:

- its input and output contracts;
- system and user prompts;
- examples where applicable;
- model selection;
- temperature and token settings;
- translation between structured Pulse state and an LLM request.

Agents should remain focused on one reasoning or generation responsibility.

Examples include capabilities such as theme extraction, planning, outlining, scripting, or metadata generation.

Provider construction does not belong inside an agent. The appropriate LLM dependency should be injected through application composition.

Prompt constants and model settings should remain local enough that similarly named constants from unrelated agents cannot collide accidentally.

### `application/`

`application/` owns Pulse use cases and composition.

This layer includes responsibilities such as:

- configuration;
- dependency assembly;
- runtime construction;
- run management;
- deployment;
- initialization;
- persistence coordination;
- operational logging.

Application code connects the other layers without turning entrypoints into business logic.

Examples include concepts such as:

```text
PulseApplication
RunManager
PodcastPipelineRuntimeFactory
deployment/
composition/
```

The application layer decides which concrete services and infrastructure implementations participate in a Pulse execution.

### `cli/`

`cli/` contains the Pulse command-line interface.

Commands such as:

```text
pulse init
pulse deploy
pulse run <pipeline-id>
pulse run resume <run-id> --pipeline-id <pipeline-id>
pulse schedule ...
```

should be thin adapters over application capabilities.

A CLI command may:

- parse arguments;
- validate command-specific input;
- call the appropriate application use case;
- render results or errors.

It should not implement the underlying deployment, scheduling, retrieval, or pipeline behavior itself.

If a feature would also be useful from another adapter, its implementation almost certainly belongs below `cli/`.

### `infrastructure/`

`infrastructure/` contains concrete integrations with external systems.

This is where Pulse implements interfaces against systems such as:

- Cloudflare D1;
- Cloudflare R2;
- Cloudflare Vectorize;
- X;
- Anthropic;
- Voyage;
- ElevenLabs;
- other provider APIs.

Infrastructure modules should implement contracts needed by the application or services rather than determining Pulse workflow behavior.

The distinction is important:

```text
service
    defines what capability it needs

infrastructure
    implements that capability for a particular external system

application
    chooses which implementation to inject
```

Avoid importing concrete infrastructure implementations directly from otherwise reusable services when dependency injection can preserve the boundary.

### `types/`

`types/` contains the current canonical Pulse data representations.

The signal lifecycle, for example, progresses through current canonical representations as information is added during processing rather than maintaining parallel copies of the same concept for every orchestration boundary.

Before adding a new type:

1. search the existing types;
2. determine whether the concept already has a canonical representation;
3. extend or compose existing types where appropriate;
4. introduce a new boundary type only when there is a real semantic boundary.

### `services/`

`services/` contains the reusable capabilities that perform Pulse's work.

Examples include:

```text
retrieval
ingestion
semantic processing
post-processing
grouping
planning support
script generation
audio production
publishing
```

A service should own one coherent capability.

Services should not need to know:

- which LangGraph node invokes them;
- what node runs next;
- whether execution came from the CLI or Cloudflare;
- how the entire application is composed.

Those concerns belong to higher layers.

### `application/orchestration/`

`application/orchestration/` contains the LangGraph episode workflow.

This is where Pulse describes:

- workflow state;
- LangGraph nodes;
- routing;
- terminal conditions;
- graph construction;
- workflow-specific result types.

The current podcast pipeline is conceptually:

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

Successful early-exit paths terminate through:

```text
complete_without_episode
    ↓
END
```

`complete_without_episode` does not continue to `commit_signals`. A no-content run does not write exact or semantic signal history.

Workflow decisions belong in `application/orchestration/` rather than inside individual services.

### `workers/`

`workers/` contains deployment-runtime adapters.

The Cloudflare Worker lives under:

```text
workers/cloudflare/
```

It owns Cloudflare-specific entrypoints and generated Worker runtime state.

The Worker should remain a thin adapter:

```text
Cloudflare Cron / Workflow
        ↓
Worker entrypoint
        ↓
application composition
        ↓
RunManager
        ↓
Pulse workflow
```

Do not duplicate pipeline logic inside the Worker.

### `tests/`

Tests are organized by scope rather than being embedded in runtime source directories.

The main layers are:

```text
tests/
├── unit/
├── integration/
└── e2e/
```

Unit tests cover the current application, CLI, infrastructure adapters, and services, including exact deduplication against `signals`.

Integration tests cover the D1 repositories against a local SQLite stand-in, and `tests/integration/test_pipeline_graph.py` runs the LangGraph publish, no-content, and resume paths with fake providers.

End-to-end tests exercise a live pipeline run and are marked `e2e`. `uv run pytest` excludes them.

See [Testing](testing.md) for the current layout and the remaining gap: there is no Worker scheduled-handler test.

Deployment code is also tested directly. Current coverage includes areas such as:

```text
tests/unit/application/deployment/
├── test_build.py
├── test_inputs.py
├── test_preflight.py
├── test_secrets.py
├── test_worker_bundle.py
└── test_wrangler.py
```

Build and deployment behavior should be changed through these tested Python components rather than through ad hoc shell scripts.

## Local environment

Pulse uses `uv` for Python dependency and environment management.

The reproducible Python environment is defined by:

```text
pyproject.toml
uv.lock
```

Node-based tooling, including Wrangler, is managed through:

```text
package.json
package-lock.json
```

Do not treat an existing `.venv`, installed package tree, or generated Worker dependency directory as source state.

## Bootstrap

A fresh checkout can be initialized with the repository bootstrap entrypoint.

On macOS or Linux:

```bash
bash bootstrap.sh
```

On Windows PowerShell:

```powershell
.\bootstrap.ps1
```

Bootstrap prepares the development environment. It requires `uv` on `PATH` and runs `uv sync`, so the Python environment matches `uv.lock`.

After bootstrap, verify the environment with:

```bash
uv run pulse --help
```

and:

```bash
uv run pytest --help
```

The bootstrap scripts are repository setup entrypoints. Runtime build and deployment logic itself lives in the tested Python application code.

## The `uv` workflow

Synchronize the environment with:

```bash
uv sync
```

Run project commands through the managed environment:

```bash
uv run pytest
```

```bash
uv run pulse --help
```

```bash
uv run pulse run <pipeline-id>
```

When Python dependencies change, update the project configuration and lockfile through `uv`.

Do not manually modify installed packages inside `.venv` as part of a permanent fix.

## Continuous integration

`.github/workflows/ci.yml` runs on push and pull request. The job uses Python 3.12 and the locked environment:

```bash
uv sync --frozen
uv run ruff check src tests bootstrap.py
uv run ruff format --check src tests bootstrap.py
uv run pyright
uv run pytest
```

That job does not deploy and does not call live providers. `uv run pytest` stays on the offline suite.

## Local execution

Run a configured pipeline locally with:

```bash
uv run pulse run <pipeline-id>
```

The execution path is approximately:

```text
CLI
 ↓
application layer
 ↓
RunManager
 ↓
PodcastPipelineRuntimeFactory
 ↓
LangGraph workflow
```

The Cloudflare scheduler and Cloudflare Workflow wrapper are not required for a normal local manual run.

This separation is intentional.

Cloudflare is a production execution adapter around the same Pulse application rather than a second implementation of the pipeline.

Resume an existing logical run with:

```bash
uv run pulse run resume <run-id> --pipeline-id <pipeline-id>
```

Pulse uses the logical `run_id` as the LangGraph `thread_id`, allowing an execution to continue using its existing checkpoint state.

## Dependency and composition boundaries

The general architecture is:

```text
               types
                  ↑
           agents / services
                  ↑
    application / orchestration
                  ↑
             cli / workers
```

`infrastructure/` provides concrete implementations of external dependencies used across these layers and is wired in through composition.

This is a dependency rule, not simply a directory hierarchy.

### Keep external systems behind infrastructure boundaries

A service that needs vector search should depend on the appropriate capability rather than creating a Cloudflare Vectorize client internally.

The same applies to:

- D1;
- R2;
- X;
- LLM providers;
- embeddings;
- TTS.

Application composition selects and supplies the concrete implementation.

### Keep workflow sequencing out of services

A service should not decide that another service must run after it because of the LangGraph topology.

That relationship belongs in `application/orchestration/`.

### Keep entrypoints thin

Both:

```text
cli/
```

and:

```text
workers/
```

translate external execution into application calls.

They should not contain independent versions of application logic.

### Keep environment-specific composition explicit

Local and Cloudflare execution can use different infrastructure implementations or checkpoint backends.

The application-facing workflow should remain the same.

Environment-specific decisions should be made during composition rather than through conditionals scattered throughout services.

## Agents

Agents deserve the same architectural discipline as conventional services.

An agent should have a narrow responsibility and a structured contract.

Prefer:

```text
typed input
    ↓
agent
    ↓
typed output
```

over passing large unstructured dictionaries through several prompting layers.

### Prompt ownership

Keep an agent's:

- system prompt;
- user prompt;
- examples;
- model configuration;
- output schema

close to that agent.

Avoid large global prompt registries unless several agents genuinely share the same behavior.

### Model configuration

Model and generation settings should be explicit.

When multiple agents expose constants such as model names, temperatures, or token limits, avoid exporting generic names into package barrels where collisions become likely.

### Agent composition

Agents should receive an LLM or provider abstraction through composition.

Do not construct the production provider directly inside the agent.

This keeps agents testable and allows local and cloud composition to remain consistent.

### Changing an agent

When an agent changes, review:

1. its structured input;
2. its structured output;
3. prompt behavior;
4. examples;
5. model settings;
6. every service or workflow node consuming its output;
7. relevant unit tests.

A prompt change can be an application-contract change when downstream code depends on structured output.

## Environment and configuration ownership

Pulse distinguishes between:

```text
committed configuration
generated configuration
runtime configuration
secrets
```

Do not blur these categories.

### Committed configuration

Examples include:

```text
pyproject.toml
uv.lock
package.json
package-lock.json
workers/cloudflare/wrangler.jsonc.template
```

These describe reproducible repository state.

### Generated configuration

The deployed Worker configuration:

```text
workers/cloudflare/wrangler.jsonc
```

is generated from Pulse configuration and the committed template.

It should not become a second manually maintained source of truth.

### Runtime configuration

Podcast shows, pipelines, and schedules are application configuration.

Their ownership belongs to Pulse rather than to hard-coded Worker configuration.

### Secrets

Secrets must not be committed in:

- source code;
- Wrangler templates;
- generated configuration intended for source control;
- test fixtures;
- documentation examples containing real values.

Pulse-specific Cloudflare API access and Wrangler authentication also have distinct ownership.

See [Deployment](../deployment.md) for the complete secret and permission model.

## Cloudflare Worker and Pyodide constraints

Cloudflare Python Workers are not equivalent to ordinary local CPython.

Code that installs and imports successfully during local development may still fail inside the Worker runtime.

Potential issues include:

- packages unavailable in Pyodide;
- compiled/native dependencies;
- differences in standard-library behavior;
- unsupported transitive dependencies;
- imports that pull in unnecessary packages;
- Worker bundle-size growth.

Worker compatibility must therefore be treated as a separate constraint from local Python correctness.

## Build the Pulse wheel

The Worker consumes a packaged Pulse build.

Create a fresh wheel with:

```bash
uv build --wheel
```

The output is written under:

```text
dist/
```

A source-code change does not automatically update an already generated Worker dependency directory.

Whenever deployed Pulse code changes, the Worker build must ultimately consume a fresh wheel.

Do not diagnose deployed behavior against a wheel built from older source.

## Worker dependency assembly

The deployment application owns construction of the Worker Python environment.

The current flow is conceptually:

```text
clean generated state
        ↓
build fresh Pulse wheel
        ↓
assemble Pyodide dependencies
        ↓
apply required compatibility packages/stubs
        ↓
install exact Pulse wheel
        ↓
workers/cloudflare/python_modules/
```

`workers/cloudflare/python_modules/` is generated output.

Do not edit it manually.

Current dependency assembly uses the Python Worker/Pyodide tooling rather than treating a shell script as the source of truth.

The deployment implementation is responsible for steps such as:

- synchronizing Pyodide-compatible dependencies;
- applying the pinned LangChain/LangGraph dependency overlay where required;
- adding compatibility stubs;
- extracting/installing the freshly built Pulse wheel.

When changing this behavior, change the deployment implementation and its tests together.

## Compatibility stubs

Some dependencies expect modules or behavior that are not available directly in the Cloudflare Python environment.

Pulse provides narrowly scoped compatibility stubs for those cases.

Current compatibility work includes modules such as:

```text
langsmith
orjson
ormsgpack
uuid_utils
websockets
xxhash
```

These stubs exist to support the subset of behavior Pulse actually requires.

A stub should remain:

- minimal;
- explicit;
- deterministic;
- tested where practical.

Do not add a compatibility stub merely to silence an import error.

First determine whether:

1. the dependency is genuinely required;
2. the import can be avoided;
3. the package can run correctly in Pyodide;
4. the behavior being stubbed is safe for Pulse.

A silently incorrect compatibility layer is worse than an explicit unsupported dependency.

## Worker bundle validation

The Worker bundle is validated before deployment.

This protects against problems such as:

- accidentally bundled virtual environments;
- excessive dependency growth;
- unrelated generated directories entering the upload;
- missing Worker Python modules;
- malformed generated build state;
- Cloudflare upload-size limits.

Bundle validation is part of the tested deployment implementation.

Relevant behavior is covered by the deployment unit tests, including:

```text
test_build.py
test_worker_bundle.py
```

When bundle behavior changes, update the implementation and tests rather than introducing a separate manual validation path.

## Bundle size and zip artifacts

There are three different artifacts worth distinguishing:

```text
source tree
    ↓
generated Worker bundle
    ↓
compressed upload/archive representation
```

The size Pulse cares about operationally is the size of the Worker bundle Cloudflare will accept.

The deployment preflight validates that bundle before Wrangler deployment.

### Where bundle-size documentation belongs

Contributor-facing details belong here because bundle growth is primarily a build and dependency concern.

[Deployment](../deployment.md) only needs to explain that deployment validates the Worker bundle before upload.

[Troubleshooting](../troubleshooting.md) should explain how to investigate an oversized bundle.

### Generated archive files

A zip or equivalent archive produced while measuring or preparing the Worker bundle is a build artifact, not application source.

It should:

- remain ignored by Git;
- be reproducible from source;
- not become a manually maintained artifact;
- not be treated as a release artifact unless Pulse explicitly introduces that contract.

If the current deployment implementation creates an archive only temporarily, its temporary location is an implementation detail and should not be relied upon by contributors.

If a stable generated bundle path is intentionally exposed by the deployment code, that path should be documented alongside the implementation that owns it.

The important developer contract is therefore:

```text
Pulse source
    ↓
fresh wheel
    ↓
fresh python_modules
    ↓
validated Worker bundle
    ↓
Wrangler upload
```

not the existence of a particular permanent `.zip` file.

### Unexpected bundle growth

When bundle size changes substantially, inspect dependency and build composition before assuming the application itself has become too large.

Common causes include:

- `.venv` entering the Worker tree;
- another development environment entering the Worker tree;
- duplicated Python packages;
- unnecessary transitive dependencies;
- `node_modules` or other unrelated output entering the build context;
- old generated Worker state surviving between builds.

Build code should start from clean generated state specifically to prevent these problems.

## Wrangler tooling

Wrangler is managed through the repository's Node dependencies.

The source template is:

```text
workers/cloudflare/wrangler.jsonc.template
```

and the generated deployment configuration is:

```text
workers/cloudflare/wrangler.jsonc
```

The deployment application is responsible for generating and validating this configuration.

Contributors should not maintain the generated file independently of its template and application configuration.

Wrangler is an infrastructure tool used by the deployment implementation; it should not become an alternative application layer.

Normal deployment should go through:

```bash
pulse deploy
```

rather than a handwritten sequence of Wrangler commands.

Direct Wrangler commands remain useful for development and diagnosis.

See [Operations](../operations.md) for runtime inspection commands.

## Deployment development

The supported deployment path is:

```bash
pulse deploy
```

At a high level, deployment performs:

```text
preflight
    ↓
validate deployment inputs
    ↓
generate / validate Wrangler configuration
    ↓
clean build state
    ↓
build fresh Pulse wheel
    ↓
assemble Worker dependencies
    ↓
validate Worker bundle
    ↓
prepare deployment secrets
    ↓
Wrangler deployment
    ↓
post-deploy verification
```

These responsibilities are implemented as application code and covered by unit tests.

When modifying deployment behavior, start with the relevant module under the deployment application package and its corresponding tests.

Avoid moving deployment behavior back into shell scripts merely because a step invokes an external command.

External commands can still be orchestrated and validated from tested Python code.

## Coding conventions

### Prefer explicit dependencies

Pass dependencies through constructors or composition.

Avoid hidden global clients and service-locator patterns.

### Keep modules focused

Services, agents, infrastructure adapters, workflow nodes, and CLI commands should each have one recognizable responsibility.

### Preserve architectural direction

Do not make lower-level models or services depend on CLI, Worker, or workflow implementations.

### Reuse canonical types

Search `src/pulse/types/` before adding a new contract.

Do not recreate structures from older Pulse architectures.

### Keep workflow state intentional

Adding a new workflow-state field affects the graph contract.

Review:

- where it is created;
- which nodes read it;
- which nodes write it;
- whether it is checkpointed;
- whether routing depends on it;
- how resume behaves.

### Keep graph behavior in `application/orchestration/`

Routing and sequencing belong to the graph.

Services should return meaningful results; the workflow decides what happens next.

### Keep infrastructure concrete

Cloudflare-, X-, Anthropic-, Voyage-, and ElevenLabs-specific code belongs behind the appropriate infrastructure boundary.

### Keep entrypoints thin

CLI and Worker code should delegate to application capabilities.

### Prefer structured logging

Use the existing scheduler, Workflow, run, and node logging conventions rather than introducing parallel lifecycle logging.

### Treat generated files as disposable

Generated artifacts should be reproducible.

Do not hand-edit a generated artifact when the correct change belongs in:

- source;
- configuration;
- deployment assembly;
- compatibility tooling.

### Avoid package-barrel side effects

Be careful with `__init__.py` exports.

Importing a package should not unexpectedly initialize providers or pull large unsupported dependencies into the Worker runtime.

This matters especially for agents, provider integrations, and Pyodide compatibility.

## Add or change a service safely

A service change usually crosses more than one file.

Work from the owning capability outward.

### 1. Identify the owning layer

Determine whether the change is really:

- a model change;
- an agent change;
- a service change;
- an infrastructure change;
- a workflow change;
- an application/composition change;
- an adapter change.

Avoid placing behavior in whichever file is easiest to reach from the current call site.

### 2. Update the canonical contract

If the service consumes or returns domain data, update the appropriate canonical model or interface.

Avoid introducing duplicate representations unnecessarily.

### 3. Implement the service behavior

Keep the implementation independent of LangGraph and entrypoint concerns.

External dependencies should be injected.

### 4. Add focused unit tests

The service should be testable without running the entire Pulse graph.

Cover:

- normal behavior;
- meaningful edge cases;
- failure behavior;
- important dependency interactions.

### 5. Update infrastructure where necessary

If the capability requires a new external operation, add or extend the appropriate infrastructure adapter.

Do not move provider-specific API behavior into the service itself.

### 6. Update composition

Wire the new dependency through the application composition and runtime factory.

Every supported runtime path should still be able to construct the application.

### 7. Update workflow integration

If the service affects pipeline state or control flow, update the relevant:

```text
workflow state
node
routing
graph builder
workflow tests
```

together.

### 8. Run the appropriate test layers

Start with the focused unit tests.

Then expand to:

- workflow tests;
- composition tests;
- integration tests;
- end-to-end tests

according to the boundaries touched by the change.

### 9. Verify Worker compatibility

If the changed code participates in deployed execution, make sure the Worker can package and import it.

A passing local test suite does not automatically prove Pyodide compatibility.

### 10. Rebuild before deployment

The safe sequence is:

```text
change source
    ↓
focused tests
    ↓
broader affected tests
    ↓
fresh wheel
    ↓
fresh Worker dependencies
    ↓
bundle validation
    ↓
deploy
    ↓
post-deploy verification
```

## Change an infrastructure adapter safely

Infrastructure changes deserve additional care because they affect external state.

When modifying a repository or provider adapter:

1. preserve its application-facing contract where possible;
2. add focused adapter tests;
3. add or update integration tests when the real storage semantics matter;
4. consider retry and idempotency behavior;
5. avoid leaking provider-specific response types upward;
6. verify Cloudflare Worker compatibility if the adapter runs there.

Changes to persistence should also be reviewed against checkpoint and resume behavior.

## Change a workflow safely

Workflow changes affect orchestration rather than a single capability.

Review all of:

```text
state
nodes
edges
conditional routing
terminal outcomes
checkpoint behavior
resume behavior
logging
tests
```

A graph that works from a fresh start can still be incorrect during resume.

When adding a node, explicitly determine:

- what state it requires;
- what state it produces;
- where checkpoint boundaries occur;
- what happens if it fails;
- whether repeating it is safe;
- which terminal outcomes can follow it.

External side effects require particular care.

For example, Pulse deliberately publishes an episode before committing the processed signals to durable consumed history:

```text
publish_episode
    ↓
commit_signals
```

Changing that ordering changes recovery semantics and should not be treated as a cosmetic graph edit.

## Development principle

Pulse should remain an application first and a Cloudflare deployment second.

The same application capabilities should be usable from:

```text
CLI
tests
Cloudflare Worker
Cloudflare Workflow
```

without reimplementing the product for each environment.

The architectural boundaries exist to preserve that property:

```text
types describe the data

agents perform focused LLM reasoning

services perform canonical capabilities

infrastructure talks to external systems

application/orchestration coordinates one episode run

application composes the product

cli and workers expose it to the outside world
```

When a change preserves those boundaries, it is usually easier to test locally, package for Pyodide, resume safely, and operate in production.