# Post-Release Bump Orchestrator

**Workflow**: `platform-lsp/.github/workflows/post-release-bump-orchestrator.yml`
**Type**: `workflow_dispatch` orchestrator (Kitfox-team operated)
**Per-app worker**: `kitfox-github/.github/workflows/post-release-bump-flow.yml` (component reference: [post-release-bump-flow.md](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/post-release-bump-flow.md))

This document is the operator runbook: when to fire the orchestrator, what inputs to supply, how to read the results, and how to recover from partial failures. For per-app worker internals (failure-reason codes, the bump sequence, auth scoping), see the flow doc.

## When to Run

Fire this orchestrator **after** `release-preparation-orchestrator.yml` has cut the release branch (e.g., `R1-2026`) from `snapshot` and **after** all team release-prep tickets have landed their constraint updates on the new release branch. At that point every app's `snapshot` branch still carries the same `pom.xml` version as the freshly-cut release branch, which causes:

1. **FAR collision** — descriptors built from `snapshot` would publish under the same coordinates as the release artifacts.
2. **Branch identity loss** — new snapshot work needs a forward-moving version lineage.

This orchestrator resolves both by, for each app in scope, reading the project version from the release branch's `pom.xml`, computing `<major>.<minor + 1>.0-SNAPSHOT`, and committing that bump directly to the `snapshot` branch.

The orchestrator is **reusable for future releases** — `release_branch` is an input, nothing is hard-coded to a specific release.

## Architecture

```
[orchestrator: platform-lsp]
  authorize ──→ setup ──→ bump (matrix) ──→ collect-results ──→ slack_notification ──→ workflow-summary
                              │
                              └──→ [flow: kitfox-github, per app]
                                     prepare-bump ──→ commit-bump (commit-and-push-changes.yml) ──→ upload_results
```

### Why split across two repos?

Mirrors `release-preparation-orchestrator.yml` (this repo) calling `release-preparation-flow.yml` (kitfox-github). The orchestrator owns "which apps and which release"; the flow owns "how to bump one app".

### Why direct commit to snapshot, not a PR per app?

The bump is a one-line, mechanical edit to `pom.xml`. App `update-config.yml` files already specify `branches.snapshot.need_pr: false` for routine snapshot updates. Reviewer overhead × 40 apps is not justified for a deterministic transformation that is fully reproducible from the inputs (`release_branch` → target version). The audit trail lives in the commit message (which references RANCHER-2951 and the release branch). If a future release calls for PR-based review, swap the per-app worker's `commit-bump` job for `commit-and-push-changes.yml` + `create-pr` without touching the orchestrator.

## Inputs

| Input | Type | Required | Default | Notes |
|---|---|---|---|---|
| `release_branch` | string | yes | — | Validated against `^R[0-9]+-[0-9]{4}$` (e.g., `R1-2026`). Drives both descriptor lookup (`platform-descriptor.json@<release_branch>`) and per-app target-version computation. |
| `additional_apps` | string | no | `''` | Apps absent from `platform-descriptor.json` that should also be bumped (comma/space/newline-separated). Used for the RANCHER-2882-pattern apps (`app-rtac-cache`, etc.) and for retry-after-fix workflows. Validated against `^app-[a-z0-9-]+$`. |
| `excluded_apps` | string | no | `''` | Apps to drop from the final list (comma/space/newline-separated). Use this to skip apps that aren't yet ready (e.g., `app-z3950` until RANCHER-2917 onboards it). |
| `dry_run` | boolean | no | `false` | When true, runs preflight + version compute + pom edit, but no commit/push and no Slack notification. The step summary and per-app result artifacts still emit. |

## App Scope

The setup job determines the target list as:

```
final = (descriptor_apps ∪ additional_apps) \ excluded_apps
```

- **`descriptor_apps`** = `[.applications.required[].name, .applications.optional[].name]` from `platform-descriptor.json` on `<release_branch>`, filtered to names matching `app-*`.
- **`additional_apps`** = the input list, validated against `^app-[a-z0-9-]+$`.
- **`excluded_apps`** = the input list. Removed last; an excluded app cannot be smuggled back in via `additional_apps`.

If the resulting list is empty, the orchestrator fails with a clear error. The full final list is logged at the start of the run for operator review — **read it before letting the matrix proceed** if you have any concerns about scope.

## How to Run

1. Confirm `release-preparation-orchestrator.yml` has completed for `<release_branch>` and that team release-prep tickets are merged.
2. Verify `platform-descriptor.json` on `<release_branch>` reflects the actual release scope (see Troubleshooting → "Stale descriptor" below).
3. Navigate to **Actions → Post-release bump orchestrator → Run workflow**.
4. Supply inputs (typical Trillium run):
   - `release_branch`: `R1-2026`
   - `additional_apps`: `app-rtac-cache` (and any other RANCHER-2882-pattern apps in scope)
   - `excluded_apps`: `app-z3950`
   - `dry_run`: **`true`** for the first invocation
5. Watch the `setup` job logs to confirm the resolved app list is correct.
6. Once dry-run passes cleanly, re-dispatch with `dry_run: false`.

## Reading the Results

### Run summary

Generated to the GitHub Actions step summary. Three sections:
- **Bumped** — apps that received a commit (links to `snapshot` tree + new version).
- **Skipped** — apps already at or above the target (with the reason).
- **Failed** — apps that failed at any stage (with `failure_reason`).

### Slack notification

Single aggregate message to the channel configured at `vars.GENERAL_SLACK_NOTIF_CHANNEL`. Color `good` if all apps succeeded; `danger` otherwise. Lists per-app PR links / failure reasons. Suppressed entirely when `dry_run: true`.

### Per-app result artifacts

Each app's flow emits a `result-<app>.json` artifact containing the full status record. Useful for post-run analysis. Schema documented in the flow doc.

## Concurrency & Parallelism

- **Concurrency group**: keyed on `release_branch` — the same release cannot be bumped twice in parallel. Different releases (theoretical) are independent.
- **`max-parallel: 10`** on the matrix — balances throughput against GitHub API rate-limit headroom.
- **`fail-fast: false`** — one bad app does not stop the rest.

## First Run / Verification

Walk these phases before relying on this orchestrator for any production release:

**Phase A — static checks**: `actionlint` and `yamllint` on both workflow files locally.

**Phase B — single-app dry run**: dispatch with `release_branch=R1-2026`, `additional_apps=app-platform-minimal`, `excluded_apps` containing every other descriptor app to narrow to one app, `dry_run=true`. Verify the step summary lists `app-platform-minimal` as "would bump" with the expected target version. Confirm no commit landed on `snapshot`.

**Phase C — single-app real run**: same trigger with `dry_run=false`. Confirm a single commit on `app-platform-minimal/snapshot` whose `pom.xml` carries the expected `<version>`. Re-run with the same inputs to verify idempotency (status `skipped`, no second commit).

**Phase D — two-app smoke**: dispatch for two apps in parallel; one should `skip` (left over from Phase C), one should `success`. Confirms `fail-fast: false` and parallelism behave correctly.

**Phase E — full release run**: clean `excluded_apps`, set `additional_apps=app-rtac-cache`, `release_branch=R1-2026`. First with `dry_run=true` to confirm preflight passes for all 40 apps; then with `dry_run=false`. Recovery: feed any failed apps back via `additional_apps` once the root cause is fixed.

**Phase F — post-bump verification**: spot-check 3 apps on the next snapshot CI cycle to confirm the new version publishes to FAR cleanly.

## Troubleshooting

### Stale `platform-descriptor.json` on the release branch

If the descriptor on `<release_branch>` lists fewer apps than the actual release scope, `setup` produces a sub-scope list. Two options:
- **Preferred**: update the descriptor on the release branch to reflect the actual scope; re-run the orchestrator.
- **Workaround**: list the missing apps in `additional_apps`. Suitable for ad-hoc fixes; not a substitute for a correct descriptor.

The `setup` job logs the final app list at start-of-run — review it before the matrix proceeds.

### Snapshot already bumped manually

The flow's idempotency check (numeric tuple comparison) handles this: status `skipped`, no commit. Snapshot is never downgraded.

### `pom.xml` version on the release branch isn't clean SemVer

If the release branch's pom carries an unexpected version format (e.g., `-RC1`, build metadata, `-SNAPSHOT`), the app fails with `pom_invalid_release_version`. The bug is on the release-prep side, not here. Investigate the release-prep run for that app before retrying.

### App in scope but missing from the descriptor

This is `app-rtac-cache`'s situation by design — RANCHER-2882 keeps it out of `platform-descriptor.json`. Use `additional_apps`.

### Partial failure — some apps succeeded, others didn't

`fail-fast: false` means the matrix completes regardless of individual failures. Read the run summary's "Failed" section, fix the root cause for each (typically a missing branch, missing descriptor entry, or a malformed pom), then re-run with the failed apps in `additional_apps` and the successful/skipped ones in `excluded_apps`. The flow's idempotency check makes re-running over already-bumped apps a no-op anyway, but narrowing keeps the run small.

## Related Workflows

- `release-preparation-orchestrator.yml` (this repo) — cuts the release branch this orchestrator depends on.
- `application-update-orchestrator.yml` (this repo) — the routine snapshot module-version updater that runs continuously. Different concern: it bumps module versions inside `application.template.json`, not the project version in `pom.xml`.
- `approve-run.yml` (this repo) — the reusable team-membership gate used by this orchestrator's `authorize` job.

## Tracking

- RANCHER-2951 — introduces this orchestrator.
- RANCHER-2917 — `app-z3950` Eureka-CI onboarding (gating its removal from `excluded_apps` for future releases).
- RANCHER-2882 — pattern for optional apps kept out of `platform-descriptor.json`.
