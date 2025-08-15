# Update Eureka Components

Resolve newer component versions from GitHub releases (respecting scope/order) when Docker images exist.

## Description

This action resolves and proposes newer versions for FOLIO Eureka components based on GitHub releases and Docker Hub image availability. It reads an input JSON array of components, fetches GitHub release tags for each repository under `folio-org`, filters candidate versions within a chosen semantic scope (major/minor/patch), sorts candidates and selects the newest version that is strictly greater than the current version, then verifies the Docker image exists on Docker Hub before including it in the output. The action ensures only validated, buildable versions are proposed for updates.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `components` | JSON array of component objects, e.g. `[{"name":"folio-kong","version":"3.9.1"}]` | Yes | - |
| `filter-scope` | SemVer scope to consider (major\|minor\|patch) | No | `patch` |
| `sort-order` | Sort order for candidate versions within scope (asc\|desc) | No | `asc` |
| `github-token` | GitHub token with at least read access (defaults to workflow GITHUB_TOKEN) | No | `${{ github.token }}` |
| `docker-username` | Docker Hub username (optional for authenticated lookups) | No | - |
| `docker-password` | Docker Hub password (optional for authenticated lookups) | No | - |
| `log-level` | Level of logging verbosity (INFO, DEBUG, WARNING, ERROR) | No | `INFO` |

## Outputs

| Output | Description |
|--------|-------------|
| `updated-components` | JSON array with updated component versions |

## Usage

### Basic Example

```yaml
- name: Update Eureka components
  id: update-components
  uses: folio-org/platform-lsp/.github/actions/update-eureka-components@master
  with:
    components: >-
      [
        {"name": "folio-kong", "version": "3.9.1"},
        {"name": "folio-keycloak", "version": "26.1.3"}
      ]
    filter-scope: 'patch'
    sort-order: 'asc'

- name: Display updated components
  run: echo '${{ steps.update-components.outputs.updated-components }}'
```

### With Custom GitHub Token

```yaml
- name: Update Eureka components with custom token
  id: update-components
  uses: folio-org/platform-lsp/.github/actions/update-eureka-components@master
  with:
    components: ${{ steps.read-descriptor.outputs.eureka_components }}
    filter-scope: 'minor'
    github-token: ${{ secrets.CUSTOM_GITHUB_TOKEN }}
    log-level: 'DEBUG'
```

### Integration with Platform Update Workflow

```yaml
- name: Read current Eureka components
  id: read-components
  run: |
    COMPONENTS=$(jq -c '.eurekaComponents' platform-descriptor.json)
    echo "components=$COMPONENTS" >> "$GITHUB_OUTPUT"

- name: Update Eureka components
  id: update-components
  uses: folio-org/platform-lsp/.github/actions/update-eureka-components@master
  with:
    components: ${{ steps.read-components.outputs.components }}
    filter-scope: ${{ inputs.scope }}
    sort-order: 'asc'

- name: Check if updates available
  id: check-updates
  run: |
    ORIGINAL='${{ steps.read-components.outputs.components }}'
    UPDATED='${{ steps.update-components.outputs.updated-components }}'
    if [[ "$ORIGINAL" != "$UPDATED" ]]; then
      echo "has_updates=true" >> "$GITHUB_OUTPUT"
    else
      echo "has_updates=false" >> "$GITHUB_OUTPUT"
    fi
```

## Behavior

### SemVer Filtering

- **patch scope**: Only considers versions that differ in the patch segment (e.g., 3.9.1 → 3.9.2)
- **minor scope**: Considers versions that differ in minor or patch segments (e.g., 3.9.1 → 3.10.0)
- **major scope**: Considers all newer versions (e.g., 3.9.1 → 4.0.0)

### Sort Order

- **asc**: Sorts candidates ascending and selects the last (most conservative upgrade)
- **desc**: Sorts candidates descending and selects the first (most aggressive upgrade)

### Docker Image Verification

Each candidate version is validated against Docker Hub before inclusion. Only versions with existing Docker images at `folioorg/<component-name>:<version>` are considered valid upgrades. This ensures proposed updates are buildable and deployable.

### Error Handling

- Missing repository: Component logged and skipped, original version retained
- No releases available: Component version unchanged
- Docker image missing for candidate: Candidate skipped, next version evaluated
- Empty input array: Returns `[]`
- Invalid JSON input: Action fails with clear error message

## Implementation Notes

- Each component triggers: 1 repository metadata call + 1 releases listing + 1 Docker Hub tag verification per candidate
- Only numeric `major.minor.patch` segments are considered for version comparison
- Non-numeric parts are coerced to `0` (e.g., `1.2.3-RC1` treated as `1.2.3`)
- Pre-release ordering is not implemented; such tags may produce unexpected ordering
- Docker authentication is optional and only needed for private images or rate-limited scenarios
- GitHub Step Summary displays run metadata when available

## License

Uses the repository license.
