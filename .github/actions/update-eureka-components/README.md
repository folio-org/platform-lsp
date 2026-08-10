# Update Eureka Components

Resolve Eureka component versions from Docker Hub against the constraints declared in the descriptor template.

## Description

This action resolves each Eureka component to the **newest published image tag satisfying the entry's constraint**. It lists the Docker Hub tags of the namespaces the entry's `preRelease` implies, discards `latest`, filters by the constraint window and the pre-release channel, and takes the maximum by semver.

There is no "leave it unchanged" path. A registry outage, an empty tag list and an all-out-of-scope tag list all fail the action, because a descriptor mixing one stale component with the rest fresh is a combination nobody validated. The action therefore never reads `platform-descriptor.json` — the template is the only input.

Every candidate is a published tag, so no separate image-existence check is needed.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `components` | JSON array from the descriptor template, e.g. `[{"name":"folio-kong","version":"^3.9.1","preRelease":"false"}]` | Yes | - |
| `docker-username` | Docker Hub username (optional; raises the anonymous rate limit) | No | - |
| `docker-password` | Docker Hub password or token | No | - |
| `log-level` | Level of logging verbosity (INFO, DEBUG, WARNING, ERROR) | No | `INFO` |

## Outputs

| Output | Description |
|--------|-------------|
| `updated-components` | JSON array of `{"name","version"}` with resolved versions |

## Usage

### Release cadence

```yaml
- name: Update Eureka components
  id: update-components
  uses: folio-org/platform-lsp/.github/actions/update-eureka-components@master
  with:
    components: >-
      [
        {"name": "folio-kong", "version": "^3.9.2"},
        {"name": "mgr-tenants", "version": "~4.0.0"}
      ]

- name: Display resolved components
  run: echo '${{ steps.update-components.outputs.updated-components }}'
```

### Pre-release cadence

```yaml
- name: Update Eureka components (snapshot)
  uses: folio-org/platform-lsp/.github/actions/update-eureka-components@master
  with:
    components: >-
      [
        {"name": "folio-kong", "version": "latest", "preRelease": "only"},
        {"name": "mgr-tenants", "version": "latest", "preRelease": "only"}
      ]
    log-level: 'DEBUG'
```

### Integration with the platform update workflow

```yaml
- name: Update Eureka components
  uses: folio-org/platform-lsp/.github/actions/update-eureka-components@master
  with:
    components: ${{ steps.read-descriptor.outputs.eureka-components }}
    docker-username: ${{ secrets.DOCKERHUB_USERNAME }}
    docker-password: ${{ secrets.DOCKERHUB_TOKEN }}
```

## Behavior

### Constraint window

| constraint | window |
|---|---|
| `latest` | none — the newest tag in the channel |
| `~4.0.0` | `>=4.0.0` and `<4.1.0-0` |
| `^3.9.2` | `>=3.9.2` and `<4.0.0-0` |
| `^4.1.0-SNAPSHOT` | `>=4.1.0-SNAPSHOT` and `<5.0.0-0` |
| `4.0.1` | exact pin — never queried |

For the range forms the prefix selects the scope and the version is the lower bound; the window matches how `semver4j` — the engine behind `/applications/validate-descriptors` — expands the range, with `includePreRelease` set as `mgr-applications` sets it.

The scope is derived from the prefix and travels on the entry itself, alongside the stem it applies to — there is no separate map to keep in sync.

A range on a pre-release branch has to anchor on a pre-release stem: under `^4.1.0` the branch's own `4.1.0-SNAPSHOT.N` builds fall below the lower bound (SemVer rule 11.3). `latest` has no such trap, which is why the `snapshot` template uses it.

Anything else — `1.x`, `>=1.0.0 <2.0.0`, `a || b` — is rejected rather than misread as an exact pin.

The constraint keyword `latest` and the Docker Hub tag literally named `latest` are unrelated. The tag alias is dropped while the tag list is being read, before any filtering, so the two can never be confused.

A `#<branch>` pin is rejected here. It is an applications-only notation: it names a branch whose `application.lock.json` holds the descriptor, and a component is a Docker image with no such artifact. The retired `check-core.sh` had no such guard and would have compared the literal as a string, judged it outdated, and overwritten it with a tag.

### `preRelease` selects the namespace

Optional per entry, defaults to `false`. Same `false` | `true` | `only` filter that `folio-application-generator` reads from an application template.

| `preRelease` | namespaces listed | candidates kept |
|---|---|---|
| `false` | `folioorg` | releases only |
| `true` | `folioorg` + `folioci`, merged before filtering | both |
| `only` | `folioci` | pre-releases only |

The channel belongs to the entry, not the branch: one branch can legitimately need both namespaces.

### Why the tag order is never trusted

Docker Hub returns tags newest-push-first, which is not newest-version-first — patches to an older line continue to be pushed after a new major ships. `folioorg/mgr-tenants` returns `3.0.8, 4.0.1, 3.0.7, 4.0.0 …`. Candidates are always re-sorted by semver.

For the same reason `latest` is discarded: on a branch pinned to `~3.0.0` it would point outside the window.

### Error Handling

The action fails — it never leaves a version unchanged — on:

- Docker Hub unreachable or non-200 after retries
- an empty tag list for a component
- a tag list where no version satisfies the entry's constraint
- invalid JSON, an unsupported constraint, or an unknown `preRelease` value
- an entry that is not exactly `{name, version}` holding concrete semver, checked by `assert_resolved` before anything is emitted

Network failures retry with exponential backoff first, honouring `Retry-After` on HTTP 429.

That last check is the only thing standing between a bug here and a corrupt descriptor. A leaked constraint does not self-heal: written into the descriptor, the next run would resolve to the same constraint the descriptor already holds, see no change, and skip everything — hourly, indefinitely. A leaked working key is worse, because `compare-components` diffs with jq's key-set-sensitive `==` (so it reports "changed" every run) while `validate-platform` and the diff report both re-project to `{name, version}` (so nothing looks wrong).

## Implementation Notes

- Tag listing follows Docker Hub pagination, 100 per page, capped at 10 pages (`folioci` holds ~138 tags today, `folioorg` 12–42); hitting the cap logs a warning
- Only numeric `major.minor.patch` segments count for comparison; non-numeric parts coerce to `0`
- Pre-release ordering is computed: `4.1.0-SNAPSHOT.2295` ranks above `...2289` and below `4.1.0`
- `preRelease` is stripped from the output, which carries only `name` and `version`
- Docker authentication is optional and only needed for private images or rate-limited scenarios
- GitHub Step Summary displays run metadata when available

## License

Uses the repository license.
