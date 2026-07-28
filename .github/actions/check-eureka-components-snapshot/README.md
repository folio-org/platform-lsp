# Check Eureka Components (Snapshot) Action

Resolves Eureka component versions for the **snapshot cadence** from Docker Hub and commits any version changes directly to the branch that the calling job checked out.

> **Transitional.** This action exists to give `ci-hourly-check.yaml` a single home for its scripts on the default branch. It is scheduled for deprecation once the snapshot branch moves onto the unified `release-scan.yml` → `release-update.yml` → `release-update-flow.yml` chain (RANCHER-3069), which resolves versions through [`update-eureka-components`](../update-eureka-components/README.md) instead. Do not build new callers on it.

## Purpose

- Reads the `eureka-components` array of `platform-descriptor.json` from the **checked-out** branch
- For each component, resolves the concrete tag that `folioci/<component>:latest` currently points at
- Commits and pushes the descriptor when any tag differs from the recorded version

### How `:latest` is resolved

Docker Hub does not expose what `latest` is an alias for, so the script infers it: it reads the `last_updated` timestamp of the `latest` tag, takes the calendar day from it, and picks the first non-`latest` tag pushed on that same day. If nothing matches, it falls back to the first non-`latest` tag in the response.

This is why the snapshot cadence reads Docker Hub rather than GitHub releases — snapshot builds never produce a GitHub release.

## Usage

```yaml
- name: Check Eureka Components Versions
  id: check-core
  uses: folio-org/platform-lsp/.github/actions/check-eureka-components-snapshot@master
  with:
    docker_username: ${{ secrets.DOCKERHUB_USERNAME }}
    docker_token: ${{ secrets.DOCKERHUB_TOKEN }}
    log_file: /tmp/check-core-output.log
```

The `@master` ref matters: it makes the action resolve from the default branch regardless of which branch the job checked out. That is what allows the snapshot branch to carry no CI of its own.

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `docker_username` | no | `''` | Docker Hub username. Only raises the anonymous rate limit; lookups work without it |
| `docker_token` | no | `''` | Docker Hub token, paired with `docker_username` |
| `log_file` | no | `/tmp/check-core-output.log` | Path the combined stdout/stderr is tee-ed to, for downstream error reporting |

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
| All components resolved | `0`, whether or not updates were applied |
| One or more components returned no usable tag | `1` — nothing committed |

Unlike the applications check, there is no interface-validation gate here; component versions are committed as soon as they resolve.

### Side effects

Writes `platform-descriptor.json.backup` next to the descriptor before applying updates, and leaves it in place. It is untracked and never committed.

## Requirements

- `jq` and `curl` on the runner
- A checkout with write credentials for the target branch, and `git config user.name` / `user.email` already set by the caller
- `fetch-depth: 0` on the checkout, so the push has the branch's history

## Related

- [`update-eureka-components`](../update-eureka-components/README.md) — the release-cadence equivalent, resolving from GitHub releases plus `folioorg` images, that will replace this action
- [`check-applications-snapshot`](../check-applications-snapshot/README.md) — the application-side counterpart
