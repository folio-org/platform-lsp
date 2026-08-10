# Update Applications

Resolve application versions from the FOLIO Application Registry (FAR) against the constraints declared in the descriptor template.

## Description

This action queries FAR for every entry it is given and resolves each one to the **newest version satisfying the entry's constraint**. It accepts either a flat array or a grouped object, and preserves that shape on output.

There is no "leave it unchanged" path. A FAR outage, an empty response and an all-out-of-scope response all fail the action, because a descriptor mixing one stale version with the rest fresh is a combination nobody validated. The action therefore never needs to know what `platform-descriptor.json` currently holds — the template is the only input.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `applications` | JSON from the descriptor template: either an array of `{"name":"app","version":"^x.y.z","preRelease":"false"}` or a grouped object `{"required":[...],"optional":[...],"<group>":[...]}` | Yes | - |
| `far-base-url` | FAR base URL | No | `https://far.ci.folio.org` |
| `far-limit` | FAR query limit (max records) | No | `500` |
| `far-latest` | FAR 'latest' query parameter (server side) | No | `50` |
| `request-timeout` | HTTP request timeout (seconds) | No | `10.0` |
| `max-retries` | Maximum number of HTTP request retries | No | `3` |
| `retry-backoff` | Base backoff time in seconds for retries | No | `1.0` |
| `log-level` | Level of logging verbosity (INFO, DEBUG, WARNING, ERROR) | No | `INFO` |

## Outputs

| Output | Description |
|--------|-------------|
| `updated-applications` | JSON (shape matches input) with possibly updated versions |

## Usage

### Basic Example with Grouped Input

```yaml
- name: Update application versions
  id: update-apps
  uses: folio-org/platform-lsp/.github/actions/update-applications@master
  with:
    applications: >-
      {
        "required": [
          {"name": "app-platform-minimal", "version": "~2.0.19"},
          {"name": "app-platform-complete", "version": "^10.1.0"}
        ],
        "optional": [
          {"name": "app-consortia", "version": "~1.2.1"}
        ]
      }

- name: Display updated applications
  run: echo '${{ steps.update-apps.outputs.updated-applications }}'
```

### Pre-release Entries (snapshot cadence)

```yaml
- name: Update application versions (flat)
  id: update-apps-flat
  uses: folio-org/platform-lsp/.github/actions/update-applications@master
  with:
    applications: >-
      [
        {"name": "app-platform-minimal", "version": "latest", "preRelease": "only"},
        {"name": "app-consortia", "version": "latest", "preRelease": "only"}
      ]
    log-level: 'DEBUG'
```

### Integration with Platform Update Workflow

```yaml
- name: Update applications from FAR
  id: update-apps
  uses: folio-org/platform-lsp/.github/actions/update-applications@master
  with:
    applications: ${{ steps.read-descriptor.outputs.applications }}
    far-base-url: ${{ env.FAR_URL }}
    log-level: 'INFO'

- name: Parse updated platform version
  id: parse-version
  run: |
    APPS='${{ steps.update-apps.outputs.updated-applications }}'
    PLATFORM_VERSION=$(echo "$APPS" | jq -r '.required[] | select(.name=="app-platform-minimal") | .version')
    echo "platform_version=$PLATFORM_VERSION" >> "$GITHUB_OUTPUT"
```

## Behavior

### Constraint window

| constraint | window |
|---|---|
| `latest` | none — the newest version in the channel |
| `~2.1.0` | `>=2.1.0` and `<2.2.0-0` |
| `^2.1.0` | `>=2.1.0` and `<3.0.0-0` |
| `^2.1.0-SNAPSHOT` | `>=2.1.0-SNAPSHOT` and `<3.0.0-0` |
| `2.1.0` | exact pin — never queried |
| `#RANCHER-2870` | branch pin — never queried, carried through verbatim |

For the range forms the prefix selects the scope and the version is the lower bound; the window matches how `semver4j` — the engine behind `/applications/validate-descriptors` — expands the range, with `includePreRelease` set as `mgr-applications` sets it.

The scope is derived from the prefix and travels on the entry itself, alongside the stem it applies to — there is no separate map to keep in sync.

A range on a pre-release branch has to anchor on a pre-release stem: under `^2.1.0` the branch's own `2.1.0-SNAPSHOT.N` builds fall below the lower bound (SemVer rule 11.3). `latest` has no such trap, which is why the `snapshot` template uses it.

Anything else — `1.x`, `>=1.0.0 <2.0.0`, `a || b` — is rejected rather than misread as an exact pin.

Note that FAR's `latest=N` query parameter (input `far-latest`) is a different thing: it caps how many recent versions the server returns.

### Branch pins

An application may be pinned to a feature branch by writing `"version": "#<branch>"`. Such an application is not in FAR — its descriptor is the `application.lock.json` committed to that branch — so this action does not query for it and carries the literal through into `platform-descriptor.json` unchanged. kitfox-github's `validate-application` resolves it from `raw.githubusercontent.com/folio-org/<app>/<branch>/application.lock.json`.

The accepted shape is narrower than git's own ref rules: letters, digits, `.`, `-`, `_`, no slashes, no `..`, no leading or trailing punctuation. A slash would break `folio-release-creator`, which builds a filename as `<app>-<version>.json`.

`#2.1.0` is rejected rather than treated as a pin — it is `^2.1.0` typed with the shift key held, and accepting it would leave the application quietly un-updated and unvalidated forever.

Branch pins apply to applications only. `update-eureka-components` rejects them: components are Docker images and have no per-branch descriptor.

RANCHER-3070 will change this from "skip" to "resolve to the version built from that branch".

### `preRelease`

Optional per entry, defaults to `false`. Same `false` | `true` | `only` filter that `folio-application-generator` reads from an application template. It is passed verbatim to FAR **and** applied to the returned candidates.

### Error Handling

The action fails — it never leaves a version unchanged — on:

- FAR unreachable or non-200 after retries
- an empty FAR response for an entry
- a response where no version satisfies the entry's constraint
- invalid JSON, an unsupported constraint, or an unknown `preRelease` value
- an entry that is not exactly `{name, version}` holding concrete semver, checked by `assert_resolved` before anything is emitted

Network failures retry with exponential backoff first (total attempts = `max-retries + 1`).

That last check is the only thing standing between a bug here and a corrupt descriptor. A leaked constraint does not self-heal: written into the descriptor, the next run would resolve to the same constraint the descriptor already holds, see no change, and skip everything — hourly, indefinitely. A leaked working key is worse, because `compare-components` diffs with jq's key-set-sensitive `==` (so it reports "changed" every run) while `validate-platform` and the diff report both re-project to `{name, version}` (so nothing looks wrong).

## Implementation Notes

- Each `(application, preRelease)` pair triggers one FAR request, cached within the run
- Only numeric `major.minor.patch` segments count for comparison; non-numeric parts coerce to `0`
- Pre-release ordering is computed: `2.1.0-SNAPSHOT.100200000011364` ranks above `...006286` and below `2.1.0`; a non-numeric trailing segment (feature builds carry a commit hash) ranks as build `0`
- `preRelease` is stripped from the output, which carries only `name` and `version`
- Output preserves the original structure (flat array or grouped object)
- GitHub Step Summary displays run metadata when available

## License

Uses the repository license.
