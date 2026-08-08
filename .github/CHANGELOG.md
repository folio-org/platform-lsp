# Changelog

All notable changes to the platform-lsp CI/CD infrastructure will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

### Changed - RANCHER-3069: Snapshot cadence folded into the release update flow

The `snapshot` branch is now an ordinary entry in `.github/update-config.yml`, processed by the
same `release-scan.yml` → `release-update.yml` → `release-update-flow.yml` chain as the release
branches. Cadence differences are inputs, not a second implementation — which is what lets
`#branch` application resolution (RANCHER-3070) be built once. Structure follows
`kitfox-github`'s `application-update-flow.yml`.

`ci-hourly-check.yaml` and the `check-applications-snapshot` / `check-eureka-components-snapshot`
actions are superseded, and removed in a follow-up once a scheduled run has been verified.

#### One flow, one model: the descriptor template is mandatory

Every branch the flow processes declares its constraints in `platform-descriptor-template.json`.
`detect-template` no longer falls back to `platform-descriptor.json` when the template is
missing — it fails, because a fallback keeps two resolution models alive.
`validate-descriptor-template` therefore always runs. The `snapshot` branch gains a template using
`latest` with `preRelease: "only"` across all six components and all three application groups.

A release branch produced by `release-preparation-orchestrator.yml` writes `platform.template.json`,
a name the flow does not look for; such a branch now fails loudly rather than silently resolving
against the descriptor. That is the pre-existing filename defect surfacing, not a new regression.

#### Resolution is now "newest in range, or fail"

The descriptor is a projection of the template, not a memory of the previous run. Each entry
resolves to the newest version satisfying its constraint; a registry outage, an empty response
and an all-out-of-scope response all stop the run.

That replaces a silent downgrade. The resolver used the template stem for two jobs — anchoring
the scope window and standing in as the version to beat — and every path that produced no update
wrote the stem back into the descriptor. With template `~2.0.0` and a descriptor holding `2.0.9`,
a FAR outage wrote **`2.0.0`** and opened a PR containing it, for every application at once.

Failing instead of preserving is deliberate: a descriptor where one application lags behind forty
others is a combination nobody validated, and it fails later at `/applications/validate-descriptors`
where the cause is much harder to see. Because nothing is ever preserved, the resolvers no longer
need to know what the descriptor currently holds.

The constraint window now carries an explicit lower bound, matching how semver4j expands the
range: `^2.1.0-SNAPSHOT` is `>=2.1.0-SNAPSHOT` and `<3.0.0-0`. Verified entry by entry against
`semver4j` 5.8.0 — the engine behind `/applications/validate-descriptors` — on the live FAR and
Docker Hub data for the R1-2026 and R1-2025-ci templates plus synthetic pre-release stems:
65 of 65 entries select the identical candidate set, comparing against
`RangesListFactory.create(range, true)`, the `includePreRelease` mode `mgr-applications` uses.
Entries declaring `latest` are outside semver4j's vocabulary and are not covered by that check.

#### `preRelease` per template entry

`folio-application-generator` already reads a `preRelease` filter (`false` | `true` | `only`) from
each application-template entry; `release-preparation-flow.yml` writes it. The platform template
has carried the same field since `release-preparation-orchestrator.yml` started writing it, and
nothing ever read it.

It is now read, defaults to `false`, and drives two things that were previously split or missing:

- the FAR `preRelease` query parameter, replacing the branch-level `far-pre-release` input
- which versions survive filtering — components had no channel filter at all, which is why the
  `-SNAPSHOT` suffix in a constraint used to be decorative
- which Docker Hub namespace is listed: `false` → `folioorg`, `only` → `folioci`, `true` → both,
  merged before filtering

`fetch_app_versions`' `@lru_cache` key includes the flag, so two entries declaring different
channels do not serve each other's answers.

The branch-level `pre_release` key stays declared and unused, exactly as it is in kitfox-github's
`application-update-flow.yml`. Cleaning up the dead keys is tracked separately.

#### One signal per decision

Each cadence difference has its own input, so no single flag silently means four things:

| decision | source |
|---|---|
| FAR pre-release filter | `preRelease` on the template entry |
| registry namespace | `preRelease` on the template entry |
| platform build numbering | `descriptor_build_offset` being non-empty, as kitfox's `-n "$OFFSET"` does |
| resolution scope | the entry's constraint prefix |
| validation gate | `need_pr` |

The version stem is read from the template rather than derived from the descriptor the workflow
itself writes, which removes a self-referential dependency on the previous run. `need_pr: false`
commits straight to the branch and skips the `package.json` rewrite (snapshot keeps deliberate
`>=` floors; only `yarn.lock` is refreshed) and the temporary FAR sync. That cadence has no PR to
gate on, so `validate-platform` — the action `release-pr-check.yml` already uses — runs inline
before anything is pushed.

#### Modified GitHub Actions

- **`update-applications`**: per-entry `preRelease`; explicit lower bound on the constraint
  window; fails instead of preserving. Pre-release-aware ordering, so
  `2.1.0-SNAPSHOT.100200000011364` ranks above `...006286` and below `2.1.0`, and a non-numeric
  trailing segment (feature builds carry a commit hash) ranks as build `0`. Plain semver ordering
  is unchanged. The `far-pre-release` input is gone.
- **`update-eureka-components`**: both cadences resolve the same way — list the Docker Hub tags of
  the namespaces implied by `preRelease`, filter by the template constraint and channel, take the
  newest by semver. The GitHub-releases path, the `docker_image_exists` gate and the `:latest`
  heuristic are removed; across all six components there were zero images without a matching
  release, so the gate never fired. Docker Hub orders tags by push time —
  `folioorg/mgr-tenants` returns `3.0.8, 4.0.1, 3.0.7, 4.0.0 …` — so candidates are always
  re-sorted by semver, which is what the `:latest` heuristic could not do. Tag listing follows
  Docker Hub pagination.
- **`calculate-version-increment`**: new `build-number` mode appending
  `descriptor_build_offset + run_number` to a version stem.
- **`validate-descriptor-template`**: covers every group under `applications`, so the
  `experimental` bucket is no longer silently skipped, and checks the `preRelease` value.

#### Constraint grammar

Supported: the keyword `latest`, a `#<branch>` pin, or `^X.Y.Z` / `~X.Y.Z` / `X.Y.Z`, each with an
optional pre-release tag such as `^2.1.0-SNAPSHOT`. `parse_constraint` now **rejects** anything else
instead of falling through to an exact pin — previously `1.x` was accepted silently and written
into the descriptor as the literal string `1.x`, and `^1.2.3 || 2.5.x` was misparsed to `1.2.0`.
Full semver range support is tracked separately.

`latest` means no window: take the newest version in the declared `preRelease` channel. It is
what the retired bash path did — `check-apps.sh` asked FAR for `latest=1` and took
`.applicationDescriptors[0].version` with no comparison at all — and it is the same keyword the
`app-*` templates already use for module versions, where `folio-application-generator` resolves
it in the descriptor-loader layer rather than through `semver4j`.

A range would have been a behavioural narrowing. `^X.Y.Z-SNAPSHOT` binds an entry to its current
major, and at release preparation nearly every application bumps its major at once, which would
stall the whole snapshot cadence until the template was regenerated by hand. Release branches
keep ranges; `snapshot` uses `latest`.

Three places had to learn the keyword, and none of them fails loudly on its own:

- `validate-descriptor-template` — allowed as a separate alternative; `CONSTRAINT_RE` stays
  semver-only
- `parse_constraint` in both resolvers — returns the keyword as its own base rather than an
  empty string, which would otherwise trip `filter_versions`' emptiness guard
- `filter_versions` — short-circuits before any version arithmetic, because
  `parse_version("latest")` quietly yields `(0, 0, 0, 1, 0)` and every bound would then be
  computed against a zero version tagged as a release

There was a fourth, `build-constraint-map`, whose `else` branch classified anything without a
`^`/`~` prefix as `exact` — so `latest` would have been silently treated as a pin and never
queried, and because that map overrode whatever the resolvers derived, teaching only
`parse_constraint` would have worked locally and been inert in CI. That action has since been
removed; see below.

#### Changed: the resolution scope travels on the entry

A constraint such as `^3.9.2` is one self-contained statement, but it used to be split in two.
The word `minor` was computed by `build-constraint-map`, emitted as a step output, passed as the
`constraint-map` input, read from an env var, JSON-parsed and merged — while the number `3.9.2`
stayed on the entry. The two halves met again only inside `filter_versions`.

The scope is now derived where the stem is, in the same call to `parse_constraint`, and attached
to the entry alongside it. `update_*` pops it exactly as it pops `preRelease`.

This was never an override mechanism in practice. `build-constraint-map` and the resolvers' own
`derived_map` were introduced in the *same* commit (RANCHER-2861, #104) and computed the same
values from the same input; the map was spread second and so always won, meaning the resolvers'
derivation was dead in CI. The optional-template fork hid this — with no template the map came
back empty — and making the template mandatory removed the fork and exposed it.

What that removes:

- the `build-constraint-map` action, its step, and the `constraint-map` input on both resolvers
- `filter-scope` — a fallback for entries missing from the map. Unreachable in CI, because the
  map covered every entry; where it *was* reachable it applied `patch` scope to an exact pin and
  resolved the pin forward
- `sort-order` — a no-op since it was introduced: `sorted(...)[0]` under `desc` and
  `sorted(...)[-1]` under `asc` are both the maximum
- `major` — a scope no code path could produce
- the name-keyed map itself, so an application appearing in two groups now gets its own scope in
  each rather than collapsing to one

**Breaking, for direct callers only.** A caller that passes `applications`/`components` without
`constraint-map` used to see a bare `X.Y.Z` entry resolved *forward* to the newest patch, because
it fell through to `filter-scope`'s `patch` default. It is now an exact pin and is never queried.
That is the intended reading of a pin, and it matches what CI already did, but it is a contract
change for anyone calling these actions directly.

#### Preserved: `#branch` pins (RANCHER-2880)

The retired `check-apps.sh` skipped an application whose version began with `#`, leaving the
literal in place and excluding it from `/applications/validate-interfaces`. Its replacement had
no such notion, which would have meant a pin in the descriptor was silently resolved away on the
next hourly run, and a pin in the template failed the run outright.

The notation is now part of the grammar. `#<branch>` is never queried and the literal reaches
`platform-descriptor.json` untouched — the descriptor for such an application is the
`application.lock.json` on that branch, which kitfox-github's `validate-application` fetches from
GitHub raw. That half of RANCHER-2880 was never affected.

Deliberately narrower than git's own ref rules: letters, digits, `.`, `-`, `_`; no slashes, no
`..`, no leading or trailing punctuation. A slash would break `folio-release-creator`, which
builds a filename as `<app>-<version>.json`. `#2.1.0` is rejected rather than accepted as a pin —
it is `^2.1.0` typed with the shift key held, and taking it at face value would leave that
application quietly un-updated and unvalidated indefinitely. The shape covers every pin this
repository has actually carried: `#MODSCHED-72`, `#RANCHER-3029`, `#RANCHER-3029-R1-2026`,
`#RANCHER-3051-SF`, `#RANCHER-3051-TR`.

Two steps skip pinned entries rather than failing on them. Both `curl` and `urllib` truncate a
URL at `#`, so a pinned version turns into a request for `/applications/<app>-`:

- **`validate-platform`** would 404 and `exit 1`, taking the whole snapshot run with it. The
  filter sits in the jq that builds the fetch list, not in the loop, so `application_count`
  reflects what is actually fetched — the same placement the retired script used, ahead of both
  its counter and its id collection. The step now warns that a pinned application's `provides`
  leave the payload with it, so pinning a platform base yields unresolved-dependency errors that
  come from the exclusion rather than from a real conflict. `check-apps.sh` had the identical
  hole; the difference is that it is now diagnosable.
- **`fetch-updated-ui-modules`** would swallow the 404 as a warning and carry on, leaving that
  application's UI modules frozen at their current `package.json` versions while the run stayed
  green and the diff report looked ordinary.

`folio-release-creator` is deliberately left alone: it exits non-zero on a failed fetch, and
packaging a tagged release whose descriptor pins a feature branch should fail loudly.

Pins are applications-only. `update-eureka-components` rejects them with a message naming the
reason — a component is a Docker image with no per-branch descriptor. `check-core.sh` had no such
guard: it would have string-compared the literal, judged it outdated and overwritten it with a
tag. `validate-descriptor-template` rejects a pinned component too, so the error lands where the
mistake is rather than one step later.

RANCHER-3070 turns this skip into a resolution to the version built from that branch.

#### Added: guards against anything but `{name, version}` reaching the descriptor

`assert_resolved` runs in both resolvers before either emits, and rejects an entry that is not
exactly `{name, version}` holding concrete semver. It is the only place that sees every entry on
every path, including the exact-pin early return.

A leaked *constraint* would not self-heal: written into `platform-descriptor.json`, the next run
would resolve the same entry to the same constraint the descriptor already holds, see no change,
and skip the write, the reports and the commit — hourly, indefinitely.

A leaked *working key* would be worse, because nothing downstream would notice. `compare-components`
diffs with jq's `==`, which is key-set sensitive, so an extra key reports "changed" on every run;
`Apply Descriptor Updates` then writes the entries verbatim; and `validate-platform` and the diff
report both re-project to `{name, version}`, so validation stays green and the report looks
ordinary. One bogus version bump and one corrupt commit later the descriptor carries the key on
both sides, the comparison balances again, and it never fails a second time. The only pre-existing
detector was `validate-platform` 404-ing on `app-acquisitions-latest`, and that job runs only for
`need_pr: false`.

`filter_versions` also rejects an unrecognised scope outright. Previously such a token fell past
both branches and silently meant "no upper bound" — a licence to jump majors.

#### Removed

- **`build-constraint-map`** — see above. It had exactly one consumer, `release-update-flow.yml`.
- `.github/scripts/validate-descriptor-template.py` and `.github/scripts/build-constraint-map.py` —
  unreferenced copies of the two composite actions' scripts, already drifted (the validator carried
  an older regex without pre-release support and iterated only `required`/`optional`). Keeping them
  would have meant two grammars diverging further with every change.

#### Notes

- The snapshot platform `version` starts moving again; it was frozen at `R2-2025-SNAPSHOT.4803`
  because the bash path never touched it.
- Platform validation widens from `/applications/validate-interfaces` to
  `/applications/validate-descriptors`.
- Replaying both cadences against live FAR and Docker Hub reproduces the current descriptors
  exactly: R1-2026's 6 components and 35 applications, and all 47 snapshot entries, resolve to
  the versions already committed.
- Three unrelated things are now spelled `latest` in the same files, and none of them is the
  other: the constraint keyword; FAR's `latest=N` query parameter, which caps how many recent
  versions the server returns; and the Docker Hub tag alias, which is discarded at fetch time
  before any filtering.

### Added - RANCHER-2324: Implement Release CI for platform-lsp

#### New GitHub Actions

- **`build-pr-body`**: Composite action for building pull request body content
- **`calculate-version-increment`**: Composite action for calculating semantic version increments
- **`check-branch-and-pr-status`**: Composite action for validating branch and PR states before operations
- **`fetch-base-file`**: Composite action for fetching base file versions for comparison
- **`fetch-updated-ui-modules`**: Composite action for retrieving updated UI module versions
- **`generate-markdown-reports`**: Composite action for generating markdown-formatted reports
- **`generate-package-diff-report`**: Composite action for generating diff reports between package.json versions
- **`generate-platform-diff-report`**: Composite action for generating collapsed diff and markdown reports comparing platform descriptors between base and head branches
- **`update-applications`**: Composite action for updating application versions by consulting the FOLIO Application Registry (FAR) respecting semver scope rules
- **`update-eureka-components`**: Composite action for resolving newer component versions from GitHub releases when Docker images exist
- **`update-package-json`**: Composite action for updating package.json dependencies
- **`validate-platform`**: Composite action for validating platform descriptor and configuration integrity

#### New Workflows

- **`release-pr-check.yml`**: Workflow for validating pull requests against release branches with comprehensive checks
- **`release-scan.yml`**: Workflow for scanning and detecting available releases that require updates
- **`release-update.yml`**: Workflow entry point for triggering release update processes
- **`release-update-flow.yml`**: Core workflow implementing the release update logic and orchestration

#### Modified Workflows

- **`release-scan.yml`**: Enhanced with proper workflow_call triggers and improved scanning logic
- **`release-pr-check.yml`**: Expanded from minimal stub to full implementation with comprehensive validation
- **`release-update-flow.yml`**: Significantly enhanced from basic implementation to full orchestration with error handling

### Changed

- **Release preparation workflows**: Refactored release preparation orchestrator to use `get-update-config` action and updated workflow version to 1.1
- **Configuration management**: Updated platform-lsp configuration templates with refined dependency and application definitions
- **Documentation**: Enhanced release preparation documentation with improved orchestration logic and result aggregation patterns

### Technical Details

**Commit History:**
- `69395bf`: RANCHER-2324 Implement release CI for platform-lsp (2025-10-30)
- `c06e422`: Update release-scan.yml (2025-10-30)
- `1d0a7e1`: Create release-update.yml (2025-10-30)
- `3fbafab`: Create release-scan.yml (2025-10-30)
- `f23d29c`: Update update-config.yml (2025-10-27)
- `25e6829`: Initialise release-pr-check flow (2025-10-27)

**Key Features:**
- Distributed CI/CD orchestration with matrix strategies
- Team authorization pattern for secure operations
- Semantic versioning scope filtering (major/minor/patch)
- Docker Hub image validation for component updates
- FAR (FOLIO Application Registry) integration for application version resolution
- Comprehensive error handling and GitHub annotations
- Result aggregation and markdown reporting
- Dry-run support for safe workflow validation

**Security:**
- Implements Team Authorization Pattern with GitHub App token generation
- Environment-based fallback with manual approval for unauthorized users
- Fail-closed by default with isolated failure handling

**Best Practices:**
- Single-responsibility jobs and steps
- YAML conventions: 2-space indentation, 120-character line limit
- Bash safety: `set -euo pipefail`, proper quoting and error handling
- Python scripts without classes/annotations for simplicity
- Comprehensive documentation with README files for all actions

---

## [Previous Releases]

_(Previous changelog entries will be added here as needed)_

