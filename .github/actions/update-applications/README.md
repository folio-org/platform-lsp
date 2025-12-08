# Update Applications

Update application versions by consulting the FOLIO Application Registry (FAR) respecting semver scope rules.

## Description

This action queries the FOLIO Application Registry (FAR) to discover newer versions for provided application entries and returns an updated JSON structure. It accepts either a flat array or grouped object of applications, fetches available versions from FAR, filters candidates by semantic versioning scope (major/minor/patch), and selects the appropriate newer version based on sort order. The action preserves the original input structure and updates versions in place where qualifying upgrades are found.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `applications` | JSON: either an array of `{"name":"app","version":"x.y.z"}` or grouped object `{"required":[...],"optional":[...],"<group>":[...]}` | Yes | - |
| `far-base-url` | FAR base URL | No | `https://far.ci.folio.org` |
| `filter-scope` | SemVer scope to consider (major\|minor\|patch) | No | `patch` |
| `sort-order` | Sort order for candidate versions within scope (asc\|desc) | No | `asc` |
| `far-limit` | FAR query limit (max records) | No | `500` |
| `far-latest` | FAR 'latest' query parameter (server side) | No | `50` |
| `far-pre-release` | Include pre-release versions (true\|false) | No | `false` |
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
          {"name": "app-platform-minimal", "version": "2.0.19"},
          {"name": "app-platform-complete", "version": "10.1.0"}
        ],
        "optional": [
          {"name": "app-consortia", "version": "1.2.1"}
        ]
      }
    filter-scope: 'patch'
    sort-order: 'asc'

- name: Display updated applications
  run: echo '${{ steps.update-apps.outputs.updated-applications }}'
```

### Basic Example with Flat Array Input

```yaml
- name: Update application versions (flat)
  id: update-apps-flat
  uses: folio-org/platform-lsp/.github/actions/update-applications@master
  with:
    applications: >-
      [
        {"name": "app-platform-minimal", "version": "2.0.19"},
        {"name": "app-consortia", "version": "1.2.1"}
      ]
    filter-scope: 'minor'
    log-level: 'DEBUG'
```

### Integration with Platform Update Workflow

```yaml
- name: Update applications from FAR
  id: update-apps
  uses: folio-org/platform-lsp/.github/actions/update-applications@master
  with:
    applications: ${{ steps.read-descriptor.outputs.applications }}
    filter-scope: ${{ inputs.scope }}
    sort-order: 'asc'
    far-pre-release: ${{ inputs.include_prerelease }}
    log-level: 'INFO'

- name: Parse updated platform version
  id: parse-version
  run: |
    APPS='${{ steps.update-apps.outputs.updated-applications }}'
    PLATFORM_VERSION=$(echo "$APPS" | jq -r '.required[] | select(.name=="app-platform-minimal") | .version')
    echo "platform_version=$PLATFORM_VERSION" >> "$GITHUB_OUTPUT"
```

## Behavior

### SemVer Filtering

- **patch scope**: Only considers versions that differ in the patch segment (e.g., 1.2.3 → 1.2.4)
- **minor scope**: Considers versions that differ in minor or patch segments (e.g., 1.2.3 → 1.3.0)
- **major scope**: Considers all newer versions (e.g., 1.2.3 → 2.0.0)

### Sort Order

- **asc**: Sorts candidates ascending and selects the last (most conservative upgrade)
- **desc**: Sorts candidates descending and selects the first (most aggressive upgrade)

### Error Handling

- FAR unreachable or non-200 response: Application version left unchanged
- No qualifying versions found: Application version unchanged
- Invalid JSON input: Action fails with clear error message
- Network failures: Automatic retries with exponential backoff (total attempts = `max-retries + 1`)

## Implementation Notes

- Each unique application name triggers one FAR request (results cached within run)
- Only numeric `major.minor.patch` segments are considered for version comparison
- Non-numeric parts are coerced to `0` (e.g., `1.2.alpha` becomes `1.2.0`)
- Pre-release ordering is not computed; `far-pre-release: true` only broadens the candidate pool
- Output preserves original structure (flat array or grouped object)
- GitHub Step Summary displays run metadata when available

## License

Uses the repository license.
