# Check Applications (Snapshot) Action

Resolves application versions for the **snapshot cadence** from the FOLIO Application Registry (FAR), validates the resulting set of application interfaces, and commits any version changes directly to the branch that the calling job checked out.

> **Transitional.** This action exists to give `ci-hourly-check.yaml` a single home for its scripts on the default branch. It is scheduled for deprecation once the snapshot branch moves onto the unified `release-scan.yml` → `release-update.yml` → `release-update-flow.yml` chain (RANCHER-3069), which resolves versions through [`update-applications`](../update-applications/README.md) instead. Do not build new callers on it.

## Purpose

- Reads `platform-descriptor.json` from the **checked-out** branch
- Queries FAR per application with `preRelease=only&latest=1` and compares against the recorded version
- Skips branch-pinned entries (`#<branch>`) for both the FAR check and interface validation
- Validates the resulting application set via `POST /applications/validate-interfaces`
- Commits and pushes the updated descriptor only if validation passes

Applications under `applications.experimental` are version-checked but deliberately **excluded** from the interface-validation payload, so an unstable experimental app cannot block the whole platform update.

## Usage

```yaml
- name: Check and Update Application Versions
  id: check-apps
  uses: folio-org/platform-lsp/.github/actions/check-applications-snapshot@master
  with:
    far_url: ${{ vars.FAR_URL }}
    log_file: /tmp/check-apps-output.log
```

The `@master` ref matters: it makes the action resolve from the default branch regardless of which branch the job checked out. That is what allows the snapshot branch to carry no CI of its own.

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `far_url` | yes | — | FAR base URL, e.g. `https://far.ci.folio.org` |
| `log_file` | no | `/tmp/check-apps-output.log` | Path the combined stdout/stderr is tee-ed to, for downstream error reporting |

## Outputs

| Output | Description |
|---|---|
| `exit_code` | Exit code of the underlying script; `0` on success |

The action itself also fails when the script fails, so `exit_code` is mainly for steps running under `if: always()` that need to attribute which step broke.

## Behavior

### Working directory

Composite action steps run with `CWD = $GITHUB_WORKSPACE`. The script therefore reads `platform-descriptor.json`, and runs `git add` / `git commit` / `git push origin "$(git branch --show-current)"`, against **the branch the calling job checked out** — not against the branch this action came from.

### Exit codes

| Condition | Result |
|---|---|
| All applications resolved, interfaces valid | `0` |
| Updates applied and pushed | `0` |
| One or more applications could not be fetched from FAR | `1` |
| Interface validation returned errors | `1` — descriptor left untouched, nothing committed |

Version drift alone is not a failure; only fetch failures and invalid interfaces are.

### Side effects

Writes `platform-descriptor.json.backup` next to the descriptor before applying updates, and leaves it in place. It is untracked and never committed.

## Requirements

- `jq` and `curl` on the runner
- A checkout with write credentials for the target branch, and `git config user.name` / `user.email` already set by the caller
- `fetch-depth: 0` on the checkout, so the push has the branch's history

## Related

- [`update-applications`](../update-applications/README.md) — the release-cadence equivalent, constraint-aware, that will replace this action
- [`check-eureka-components-snapshot`](../check-eureka-components-snapshot/README.md) — the component-side counterpart
- [`validate-platform`](../validate-platform/README.md) — the FAR validation used by the release flow
