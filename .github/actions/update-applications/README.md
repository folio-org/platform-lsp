# Update Applications (Composite GitHub Action)

Queries the FOLIO Application Registry (FAR) to discover newer versions for provided application entries and returns an updated JSON structure.

## What it does
1. Accepts input JSON: either
   - Flat array: `[{"name":"app-platform-minimal","version":"2.0.19"}, ... ]`
   - Grouped object: `{ "required":[...], "optional":[...], "other":[...] }`
2. For each application `name`, calls FAR `GET /applications` with filters.
3. Extracts version list from typical FAR payload shapes.
4. Filters candidates by semantic scope (`major|minor|patch`).
5. Chooses a newer version (if any) based on selected sort order.
6. Mutates versions in-place and outputs JSON shaped like the input.

## Inputs
| Name | Required | Default | Type | Description |
|------|----------|---------|------|-------------|
| applications | yes | — | JSON string | Flat array or grouped object of objects with `name` and `version` |
| far-base-url | no | https://far.ci.folio.org | string | FAR base endpoint (HTTPS) |
| filter-scope | no | patch | choice | `major`, `minor`, or `patch` scope constraint |
| sort-order | no | asc | choice | `asc` picks last after ascending sort; `desc` picks first after descending sort |
| far-limit | no | 500 | integer (string) | FAR `limit` parameter (max records) |
| far-latest | no | 50 | integer (string) | FAR `latest` parameter (server-side) |
| far-pre-release | no | false | boolean (string) | Include pre-release versions in FAR query |
| request-timeout | no | 10.0 | float (string) | Per-request timeout seconds |
| max-retries | no | 3 | integer (string) | Retry attempts on network errors (total attempts = `max-retries + 1`) |
| retry-backoff | no | 1.0 | float (string) | Base backoff seconds; exponential growth with small jitter |
| log-level | no | INFO | choice | `DEBUG`, `INFO`, `WARNING`, `ERROR` logging verbosity |

## Output
| Name | Description |
|------|-------------|
| updated-applications | JSON matching original shape (grouped or flat) with updated versions where upgrades found |

## Example (grouped input)
```yaml
- name: Update app versions
  id: apps
  uses: ./.github/actions/update-applications
  with:
    applications: >-
      {"required":[{"name":"app-platform-minimal","version":"2.0.19"}],"optional":[{"name":"app-consortia","version":"1.2.1"}]}
    filter-scope: patch
    sort-order: asc
```

## Example (flat input)
```yaml
- name: Update flat list
  id: appsflat
  uses: ./.github/actions/update-applications
  with:
    applications: >-
      [{"name":"app-platform-minimal","version":"2.0.19"},{"name":"app-consortia","version":"1.2.1"}]
```

## Sample follow-up usage
```yaml
- name: Print updated
  run: echo '${{ steps.apps.outputs.updated-applications }}'

- name: Use specific apps
  run: |
    APPS='${{ steps.apps.outputs.updated-applications }}'
    PLATFORM_VERSION=$(echo "$APPS" | jq -r '.required[] | select(.name=="app-platform-minimal") | .version')
    echo "Using platform version $PLATFORM_VERSION"
```

## SemVer handling
- Only numeric segments considered: `major.minor.patch`
- Non-numeric parts coerced to `0` (e.g. `1.2.alpha` -> `(1,2,0)`)
- Pre-release ordering is not computed; enabling `far-pre-release: true` only broadens the candidate pool.

## Edge cases
| Scenario | Behavior |
|----------|----------|
| FAR unreachable | Application left unchanged (empty version list) |
| No versions returned | Unchanged |
| No candidate in scope | Unchanged |
| Invalid JSON input | Action fails early with clear error message |
| Mixed grouping keys | All preserved and updated in-place |
| Network issues | Automatic retries (total attempts = `max-retries + 1`) with exponential backoff |

## Performance
- Each app triggers one FAR request (cached per unique `name`).
- Caching prevents duplicate API calls within run.
- Batch all apps in a single action step to limit overhead.
- Dependency caching accelerates repeated pipeline usage.

## Local development
```bash
cd .github/actions/update-applications
python3 update-applications.py  # demo mode (requires APPLICATIONS_JSON env)

APPLICATIONS_JSON='[{"name":"app-platform-minimal","version":"2.0.19"}]' \
FILTER_SCOPE=patch SORT_ORDER=asc python3 update-applications.py
```

Install dependencies:
```bash
pip install 'requests>=2.31.0,<3.0.0'
```

## Troubleshooting
| Symptom | Possible Cause | Mitigation |
|---------|----------------|-----------|
| HTTP non-200 | FAR base URL incorrect / service issue | Verify `far-base-url`, retry |
| No updates found | Scope too narrow | Try `filter-scope: minor` or `major` |
| Timeout | Network latency | Increase `request-timeout` |
| Pre-releases missing | Not included | Set `far-pre-release: true` |
| Network failures | Transient connectivity | Increase `max-retries` |
| Unexpected version order | Sort semantics | Adjust `sort-order` |

## Security and Reliability
- Validates scope & sort inputs; fails closed on malformed JSON.
- Automatic retries with exponential backoff and jitter.
- Timeouts prevent hanging requests.
- GitHub Step Summary provides run metadata.
- No secrets processed; FAR queries are public.

## Notes
- Output groups may appear key-sorted due to JSON serialization (ordering is not guaranteed for consumers).
- Logic intentionally leaves unchanged apps when FAR data is unavailable.

## License
Inherits repository license.
