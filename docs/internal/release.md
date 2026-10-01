# Release

This guide defines the release checklist for Pulse.

A Pulse release is not complete when the package builds or the test suite passes. The release candidate must also survive the production deployment path, execute through the deployed scheduler and Cloudflare Workflow, publish a real episode, and expose valid podcast artifacts over the public feed.

The release sequence therefore validates progressively larger boundaries:

```text
repository
    ↓
tests
    ↓
package build
    ↓
Worker build
    ↓
Cloudflare deployment
    ↓
scheduler + Workflow
    ↓
Pulse graph
    ↓
publishing
    ↓
RSS / audio / artwork
    ↓
Spotify
```

Do not tag a commit that differs from the commit used for final deployment verification.

## Release checklist

Before publishing a release, complete all of the following:

- [ ] Repository cleanup
- [ ] Dependency review
- [ ] Secret scan
- [ ] Full test pass
- [ ] Package and Worker build pass
- [ ] Clean `pulse deploy`
- [ ] Scheduled smoke run
- [ ] RSS verification
- [ ] Audio verification
- [ ] Artwork verification
- [ ] Spotify verification
- [ ] Documentation review
- [ ] Version finalized
- [ ] Release notes prepared
- [ ] Release commit finalized
- [ ] Git tag created from the verified commit
- [ ] Final clean `git status`

## 1. Clean the repository

Start from a repository state that contains only intentional source changes.

Review:

```bash
git status
git diff
git diff --cached
```

Remove accidental development artifacts before release.

Pay particular attention to:

- temporary files;
- local database files;
- editor artifacts;
- debug output;
- downloaded provider responses;
- generated Worker state;
- locally generated archives;
- `.env` files;
- credentials;
- obsolete files left behind by refactors.

Generated deployment artifacts should not become release source merely because they exist locally.

This includes generated state such as:

```text
workers/cloudflare/python_modules/
wrangler.jsonc
dist/
```

and any temporary Worker bundle or archive produced during build validation.

The repository should be reproducible from committed source and lockfiles.

## 2. Review dependencies

Review both Python and Node dependencies.

Python dependency state is defined by:

```text
pyproject.toml
uv.lock
```

Node tooling is defined by:

```text
package.json
package-lock.json
```

Check for:

- dependencies added unintentionally;
- dependencies no longer used;
- unnecessary development dependencies entering runtime requirements;
- unexpected lockfile changes;
- duplicate or conflicting packages;
- dependencies that may not be compatible with Cloudflare's Python/Pyodide runtime.

Dependency review is especially important for Worker code because a seemingly small Python dependency can significantly affect the generated Worker bundle or introduce unsupported transitive imports.

If dependencies changed, make sure the Worker-specific build and compatibility tests are exercised before release.

## 3. Scan for secrets

No release commit should contain production credentials.

Inspect the staged and unstaged changes for:

- Cloudflare API tokens;
- provider API keys;
- account-specific credentials;
- generated Wrangler secrets;
- `.env` contents;
- credentials copied into tests or fixtures;
- secrets accidentally included in documentation or logs.

Useful repository-level checks include:

```bash
git diff
git diff --cached
git status --ignored
```

Pay particular attention to generated configuration.

The committed:

```text
workers/cloudflare/wrangler.jsonc.template
```

must not contain secrets.

The generated:

```text
workers/cloudflare/wrangler.jsonc
```

must not become a committed secret store.

Worker runtime secrets should remain managed through the deployment secret flow.

## 4. Run the full test suite

A release candidate should pass the offline test suite:

```bash
uv run pytest
```

That command excludes the live end-to-end test. On a machine with provider credentials, also run:

```bash
uv run pytest -m e2e
```

Do not rely only on the tests closest to the most recent change.

Pulse now has meaningful coverage across:

```text
unit
integration
end-to-end
```

The release pass should cover the current architecture, including where applicable:

- agents;
- services;
- infrastructure adapters;
- canonical types;
- application composition;
- LangGraph nodes and routing;
- graph orchestration;
- checkpoint-sensitive behavior;
- repositories;
- scheduler behavior;
- deployment inputs and preflight;
- Worker build assembly;
- bundle validation;
- Wrangler configuration;
- secrets handling;
- logging;
- end-to-end pipeline execution.

A release-blocking failure should be fixed rather than hidden with a skipped or weakened test unless the test itself is demonstrably incorrect.

After fixing a failure, rerun the affected tests and then the complete suite.

## 5. Verify the package and Worker build

Build the Pulse wheel from the release candidate:

```bash
uv build --wheel
```

Confirm that the package builds without relying on stale local state.

The production Worker build has additional constraints beyond the Python wheel.

The deployment build must be able to:

```text
build fresh Pulse wheel
        ↓
assemble Pyodide-compatible dependencies
        ↓
apply required compatibility stubs
        ↓
install the exact Pulse wheel
        ↓
construct fresh python_modules
        ↓
validate the Worker bundle
```

This behavior is owned by the tested Python deployment implementation.

Do not manually repair generated `python_modules` as part of preparing a release.

If the generated Worker environment is wrong, fix the build implementation, dependency configuration, or compatibility layer that produced it.

### Bundle size

Review the bundle-validation result during the release build.

A significant unexplained increase should be investigated before deployment.

Typical causes include:

- duplicated dependencies;
- unintended development packages;
- generated environments entering the bundle;
- old build state;
- newly introduced transitive dependencies.

Any zip or equivalent archive created during validation is generated build output unless Pulse explicitly defines it as a release artifact.

The release does not require committing or preserving that archive.

## 6. Perform a clean deployment

Deploy the release candidate using the supported Pulse deployment path:

```bash
pulse deploy
```

The release must use the same deployment path intended for normal users and operators.

Do not replace this gate with a collection of hand-executed Wrangler commands.

The deployment path should exercise:

```text
preflight
    ↓
deployment input validation
    ↓
Wrangler configuration generation
    ↓
fresh package build
    ↓
fresh Worker dependency assembly
    ↓
bundle validation
    ↓
secret synchronization
    ↓
Worker / Workflow / Cron deployment
    ↓
post-deploy verification
```

A successful `uv build` is not a substitute for a successful `pulse deploy`.

Likewise, Wrangler accepting the upload is not sufficient if Pulse's post-deploy verification fails.

Resolve failed verification before continuing the release.

## 7. Run a scheduled smoke test

The final smoke test must exercise the **deployed scheduled execution path**, not only:

```bash
pulse run <pipeline-id>
```

A manual run proves the application/runtime path, but it does not prove the production scheduler or Cloudflare Workflow integration.

The scheduled smoke path should exercise:

```text
Cloudflare Cron heartbeat
        ↓
Pulse scheduler
        ↓
Cloudflare Workflow instance
        ↓
run-pipeline
        ↓
RunManager
        ↓
LangGraph
        ↓
episode publication
        ↓
signal-history commit
```

Use the release-smoke pipeline or other configuration intended for deployment verification.

Do not casually modify a production podcast schedule merely to perform a release test.

### Observe the scheduler

Tail the deployed Worker while the smoke run becomes due:

```bash
npx wrangler@latest tail pulse-worker \
  --config workers/cloudflare/wrangler.jsonc
```

Confirm that the scheduler:

1. receives the Cron heartbeat;
2. discovers the due schedule;
3. dispatches the pipeline;
4. advances the schedule correctly.

Then confirm that a Cloudflare Workflow instance was created.

### Inspect the Workflow instance

List instances:

```bash
npx wrangler@latest workflows instances list pulse-pipeline \
  --config workers/cloudflare/wrangler.jsonc
```

Inspect the smoke instance:

```bash
npx wrangler@latest workflows instances describe pulse-pipeline <instance-id> \
  --config workers/cloudflare/wrangler.jsonc
```

For scheduled executions, the identity should remain correlated across:

```text
Cloudflare Workflow instance ID
            =
Pulse run_id
            =
LangGraph thread_id
```

Confirm that the outer Workflow completed successfully and that the Pulse result reports:

```text
workflow_outcome = published
```

### `no_content` is not enough for the release smoke

A run that completes with:

```text
workflow_outcome = no_content
```

is a valid application outcome.

However, it is **not sufficient as the final release smoke test**, because it does not exercise the complete publication path.

The release smoke should reach:

```text
produce_audio
    ↓
publish_episode
    ↓
commit_signals
```

so that audio generation, publication, R2 access, RSS mutation, and post-publication signal commit are all validated.

If the scheduled smoke unexpectedly returns `no_content`, investigate the reason or use the designated smoke configuration with suitable fresh input before completing the release.

## 8. Verify the Pulse run

Follow the smoke run by `run_id`.

Confirm normal run lifecycle events:

```text
run_started
...
run_completed
```

There should be no unexpected:

```text
run_failed
node_failed
workflow_attempt_failed
```

events for the final successful attempt.

Review the node sequence and make sure the graph reaches:

```text
publish_episode
    ↓
commit_signals
```

The order matters.

Publishing occurs before Pulse records those signals as consumed. A release smoke that publishes but fails during final signal commit should therefore be investigated rather than treated as completely healthy.

## 9. Verify RSS

Fetch the deployed show's RSS URL directly:

```bash
curl -i https://<podcast-host>/shows/<show-id>/rss.xml
```

Validate the XML:

```bash
curl -fsSL https://<podcast-host>/shows/<show-id>/rss.xml \
  | xmllint --noout -
```

Confirm that:

- the feed is publicly accessible;
- the document is valid XML;
- the smoke episode appears;
- the episode metadata is correct;
- the episode GUID is present;
- the enclosure URL is correct;
- the expected show artwork is referenced.

Do not use Spotify as the first RSS diagnostic.

The public Pulse feed should be independently healthy before checking downstream ingestion.

## 10. Verify audio

Take the enclosure URL directly from the RSS item.

Check it over public HTTPS:

```bash
curl -I "<audio-url>"
```

Confirm that:

- the request succeeds;
- no Cloudflare API credentials are required;
- the content type is appropriate;
- the object is the expected episode audio.

If needed, download part or all of the object and verify that it is valid audio.

An RSS feed that contains an inaccessible enclosure does not pass the release gate.

## 11. Verify artwork

Take the artwork URL from the published RSS feed:

```bash
curl -I "<artwork-url>"
```

Confirm:

- successful public access;
- appropriate image content type;
- expected artwork content.

Artwork should not depend on authenticated Cloudflare API access.

## 12. Verify Spotify

After the public Pulse artifacts are healthy, verify the podcast through Spotify.

Confirm that:

- the show still loads;
- the feed has not been rejected;
- existing episodes remain available;
- the smoke episode appears after Spotify refreshes the feed;
- the episode plays correctly;
- artwork displays correctly.

Distinguish a Pulse publishing failure from normal downstream feed-refresh delay.

The authoritative release checks remain the public RSS and referenced assets. Spotify verification confirms that the downstream consumer can ingest that output successfully.

Do not republish duplicate episodes merely to force a faster Spotify refresh.

## 13. Review documentation

Review documentation against the release candidate rather than against intended behavior.

At minimum, check:

```text
README.md
docs/getting-started.md
docs/configuration.md
docs/deployment.md
docs/operations.md
docs/troubleshooting.md
docs/architecture/
docs/internal/development.md
docs/internal/testing.md
docs/internal/release.md
CONTRIBUTING.md
```

Confirm that:

- CLI commands still exist;
- examples use current argument names;
- current `types/` terminology is used;
- removed directories or legacy DTOs are not referenced;
- workflow node names match the implementation;
- the current scheduler architecture is represented correctly;
- checkpoint/resume behavior is described accurately;
- deployment ownership reflects the Python deployment implementation;
- generated artifacts are not presented as source files;
- Cloudflare resource names are current;
- internal links resolve.

If architecture diagrams changed, confirm that the exported diagram assets used by Pulse documentation match the current `pulse-diagrams` source.

Do not document aspirational behavior as though it already exists.

## 14. Finalize the version

The exact commit that was tested and deployed should be the commit that is released.

If Pulse stores its package version in source, finalize that version **before the final build and deployment verification** so that the deployed artifact contains the release version.

After changing a version:

```bash
uv sync
uv run pytest
uv build --wheel
```

and repeat any deployment verification invalidated by that change.

Do not:

1. verify one commit;
2. modify release-bearing source;
3. tag the modified commit without retesting it.

There should be one canonical version source rather than several manually synchronized version values.

## 15. Prepare release notes

Release notes should explain what changed from the previous release.

Include the items that matter to users and operators, such as:

- notable features;
- behavior changes;
- CLI changes;
- configuration changes;
- architecture changes that affect contributors;
- dependency or runtime changes;
- deployment changes;
- migration requirements;
- operational considerations;
- fixed defects;
- known limitations.

Avoid turning release notes into a raw commit log.

Call out breaking configuration or deployment changes prominently.

For changes to persistence, workflows, or scheduling, explain any action an existing deployment must take before or after upgrading.

## 16. Finalize the release commit

Before tagging, inspect the exact release diff:

```bash
git status
git diff
git diff --cached
```

Confirm that the commit contains:

- intended source changes;
- intended tests;
- intended documentation;
- required lockfile changes;
- version changes, where applicable.

Confirm that it does **not** contain:

- generated Worker dependencies;
- local Wrangler configuration;
- build archives;
- wheels;
- credentials;
- debug files;
- accidental fixture changes.

Create the final release commit using the repository's normal commit workflow.

If this changes the commit that was deployed during verification, determine whether the change affects runtime behavior.

Documentation-only release-finalization changes may not require another production smoke run. Runtime, dependency, configuration, build, or deployment changes do.

## 17. Create the Git tag

Create the release tag from the exact verified release commit.

Before tagging:

```bash
git status
git log -1 --oneline
```

Confirm that `HEAD` is the intended release commit.

Use the repository's established tag naming convention.

Do not move an existing published release tag to a different commit.

The tag should identify the source from which the validated release was built.

## 18. Final clean state

Finish with:

```bash
git status
```

The repository should report a clean working tree.

Also verify that no generated release artifacts have accidentally become tracked:

```bash
git status --ignored
```

The final state should satisfy:

```text
tests passed
deployment passed
scheduled smoke passed
public artifacts passed
Spotify passed
documentation reviewed
release commit identified
tag points to verified commit
working tree clean
```

At that point the release is complete.

## Release principle

Pulse has several layers that can succeed independently:

```text
package build
Worker build
deployment
scheduler
Cloudflare Workflow
LangGraph
publication
public hosting
Spotify ingestion
```

A release should not infer success in one layer from success in another.

The release process deliberately crosses every production boundary once so that the tagged commit represents code that has not only been tested, but has actually completed Pulse's intended production lifecycle.