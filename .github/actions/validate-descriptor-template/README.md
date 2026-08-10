# Validate Descriptor Template

Check the constraint grammar of a platform descriptor template, and report whether the branch is ready to be resolved.

## Description

Reads `platform-descriptor.template.json` and answers one of three things:

| outcome | exit | `valid` | meaning |
|---|---|---|---|
| ready | 0 | `true` | every constraint is resolvable |
| not yet | 0 | `false` | the template still carries release-preparation placeholders |
| wrong | 1 | `false` | a constraint is malformed |

The middle row is the point of the action. `release-preparation-orchestrator.yml` seeds a new release branch with `^VERSION_<x>` versions for a human to replace once the real component versions are known. Until that happens the branch cannot be updated — but it is not broken either, so failing the scheduled run every hour would be noise. The caller skips the branch instead.

A malformed constraint is a different answer and still fails, because nobody is going to fix it by waiting.

This mirrors `generate-application-descriptor` in kitfox-github, which applies the same warn-and-skip to `application.template.json`.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `template-file` | Path to the descriptor template JSON file | Yes | - |

## Outputs

| Output | Description |
|--------|-------------|
| `valid` | `true` when the template is ready to resolve; `false` for both "not yet" and "wrong" |
| `failure_reason` | Why it is not usable, naming the offending entries; empty when valid |

## Usage

```yaml
- name: 'Validate descriptor template'
  id: validate-template
  uses: folio-org/platform-lsp/.github/actions/validate-descriptor-template@master
  with:
    template-file: platform-descriptor.template.json

- name: 'Resolve versions'
  if: steps.validate-template.outputs.valid == 'true'
  uses: ./.github/actions/update-applications
  with:
    applications: ${{ steps.read-descriptor.outputs.applications }}
```

Gate only the steps that would break on an unresolvable constraint. In `release-update-flow.yml` that is three — the two resolvers and `compare-components` — because everything after them already keys off `updated`, which is empty when the resolvers are skipped. `manage-pr` needs its own gate: it runs under `always()` with a disjunction and would otherwise open a PR titled "Release: Update to No updates".

## What it checks

### Top-level `version`

Plain `X.Y.Z`, or `Rx-YYYY` optionally followed by a suffix, a `-SNAPSHOT` marker and a build segment — `R1-2026.1`, `R1-2025-ci.1`, `R2-2025-SNAPSHOT`.

The pattern is **anchored**, deliberately. `release-update-flow` feeds this value to `calculate-version-increment`, whose pattern requires a trailing `.<number>`; while it was unanchored a bare `R1-2026` passed here and then matched nothing there, so the branch reported no update and committed nothing on every run.

### Entry versions

Applied to `eureka-components` and every group under `applications`, including `experimental`.

| form | verdict |
|---|---|
| `latest` | valid |
| `^X.Y.Z`, `~X.Y.Z`, `X.Y.Z`, each with an optional pre-release tag | valid |
| `#<branch>` | valid **for applications only** |
| `^VERSION_…`, `${…}` | pending |
| anything else | invalid |

A branch pin on a component is rejected here rather than left to the resolver: a pin names a branch whose `application.lock.json` holds the descriptor, and a component is a Docker image with no such artifact. Catching it here puts the error where the mistake is.

Pin shape is narrower than git's own ref rules — letters, digits, `.`, `-`, `_`; no slashes, no `..`, no leading or trailing punctuation. A slash would break `folio-release-creator`, which builds a filename as `<app>-<version>.json`. `#2.1.0` is rejected as a pin: it is `^2.1.0` typed with the shift key held.

Full semver ranges (`>=1.0.0 <2.0.0`, `1.x`, `a || b`) are not supported and are rejected rather than misread; that is tracked separately.

### `preRelease`

Optional per entry. Must be `false`, `true` or `only` — the `PreReleaseFilter` values `folio-application-generator` defines.

## License

Uses the repository license.
