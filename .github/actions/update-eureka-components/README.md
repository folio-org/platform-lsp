# Update Eureka Components (Composite GitHub Action)

Resolve and propose newer versions for FOLIO Eureka components based on GitHub releases and existing Docker Hub images.

## What it does
1. Reads an input JSON array of components: [{"name":"repo","version":"x.y.z"}, ...]
2. Fetches GitHub release tags for each repository in org `folio-org` (strips leading `v`).
3. Filters candidate versions within a chosen semantic scope (major / minor / patch).
4. Sorts candidates (asc/desc) and selects the newest that is strictly greater than current.
5. Verifies the Docker image tag exists in `folioorg/<name>:<version>` on Docker Hub.
6. Emits an updated JSON array (possibly unchanged) as the `updated-components` output.

## Inputs
- components (required)  
  JSON array: e.g. `[ {"name":"folio-kong","version":"3.9.1"} ]`
- filter-scope (default: patch)  
  One of: major | minor | patch
- sort-order (default: asc)  
  `asc` sorts ascending and uses the last element (newest); `desc` sorts descending and uses the first element.
- github-token (default: workflow GITHUB_TOKEN)  
  Needs repo read access to list releases (default token usually sufficient)
- docker-username / docker-password (optional)  
  Only needed if private or rate‑limited access appears; otherwise anonymous queries are attempted.
- log-level (default: INFO)  
  Controls verbosity (`INFO`, `DEBUG`, `WARNING`, `ERROR`). Passed via env and respected by the Python script.

## Output
- updated-components  
  JSON array mirroring input order with any upgraded version numbers.

## Example workflow usage
```yaml
name: Update Eureka Components
on:
  workflow_dispatch: {}
  schedule:
    - cron: '0 6 * * *'

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Compute updates
        id: eureka
        uses: ./.github/actions/update-eureka-components
        with:
          components: >-
            [{"name":"folio-kong","version":"3.9.1"},{"name":"folio-keycloak","version":"26.1.3"}]
          filter-scope: patch
          sort-order: asc
          log-level: INFO

      - name: Show result
        run: |
          echo "Updated components: ${{ steps.eureka.outputs.updated-components }}"
```

## Interpreting results
If `updated-components` equals the original input, no qualifying newer images were found (or none passed Docker image existence check). Differences indicate candidate upgrades.

## SemVer notes / limitations
- Only numeric `major.minor.patch` parts are considered.
- Non-numeric segments (e.g. `1.2.3-RC1`) are coerced with non-numeric portions treated as 0.
- Pre-release ordering is not implemented; such tags may produce unexpected ordering if present.

## Edge cases handled
- Missing repo: logged and skipped, original version retained.
- No releases: component unchanged.
- Docker image for candidate version missing: candidate skipped.
- Empty input array: returns `[]`.
- Invalid JSON input: action fails fast with clear message.

## Security & permissions
- Uses provided `github-token` (defaults to ephemeral workflow token) for release listing.
- Avoids exposing secrets in logs; Docker credentials are optional.
- No write operations (no commits / tags) performed—purely computational.

## Performance considerations
- Each component triggers: 1 repo metadata call + 1 releases call + (at most) 1 Docker Hub tag probe.
- For many components, network latency dominates; consider batching or caching externally if scaling.

## Local development
```bash
cd .github/actions/update-eureka-components
python3 update-eureka-components.py  # demo mode (will error without data)

# Provide explicit JSON input
COMPONENTS_JSON='[{"name":"folio-kong","version":"3.9.1"}]' \
  FILTER_SCOPE=patch SORT_ORDER=asc LOG_LEVEL=DEBUG \
  python3 update-eureka-components.py --filter-scope "$FILTER_SCOPE" --sort-order "$SORT_ORDER" --data "$COMPONENTS_JSON"
```
Install deps locally:
```bash
pip install -r requirements.txt
```

## Troubleshooting
| Symptom | Cause | Action |
|---------|-------|--------|
| Invalid JSON error | Malformed `components` input | Validate JSON string (lint / echo / jq) |
| Repository not found | Name mismatch / private repo | Confirm repo exists under `folio-org` |
| No updates found when expected | Scope too restrictive | Try `filter-scope: minor` or `major` |
| Candidate skipped (Docker image missing) | Release created before image published | Re-run later or verify CI build |
| Excessive retries / slow | Transient API/network issues | Examine logs at `DEBUG` level |

## Updating / version pinning
Reference by commit SHA in consuming workflows for deterministic behavior. Example:
```yaml
uses: folio-org/platform-lsp/.github/actions/update-eureka-components@<commit-sha>
```

## Exit codes
- 0 success (even if no updates)
- Non-zero for invalid input or unrecoverable environment misconfiguration.

## Future enhancements (ideas)
- Support pre-release / build metadata ordering.
- Add option to emit changelog URLs.
- Optional matrix expansion for downstream jobs.

## License
This action inherits the repository's license. Review root LICENSE file.

---
### Maintenance Notes
- Business logic intentionally unchanged during refactoring; improvements limited to clarity & logging.
- Retry strategy uses exponential backoff with lightweight jitter; adjust constants near top if needed.
