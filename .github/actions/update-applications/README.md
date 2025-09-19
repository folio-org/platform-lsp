# Update Applications (Composite GitHub Action)

Queries the FOLIO Application Registry (FAR) to discover newer versions for provided application entries and returns an updated JSON structure.

## What it does
1. Accepts input JSON: either
   - Flat array: `[ {"name":"app-platform-minimal","version":"2.0.19"}, ... ]`
   - Grouped object: `{ "required":[...], "optional":[...], "other":[...] }`
2. For each application `name`, calls FAR `GET /applications` with filters.
3. Extracts version list from typical FAR payload shapes.
4. Filters candidates by semantic scope (major|minor|patch).
5. Chooses a newer version (if any) based on selected sort order.
6. Mutates versions in-place and outputs JSON shaped like the input.

## Inputs
- applications (required)
  JSON string: flat array or grouped object.
- far-base-url (default: https://far-test.ci.folio.org)
- filter-scope (default: patch)
  major | minor | patch
- sort-order (default: asc)
  asc chooses the highest (last) after sorting ascending; desc uses first element of descending list.
- far-limit (default: 500)
  FAR limit parameter.
- far-latest (default: 50)
  FAR 'latest' parameter.
- far-pre-release (default: false)
  Whether to include pre-release versions.
- request-timeout (default: 10.0)
  HTTP timeout in seconds.

## Output
- updated-applications
  JSON matching original shape (grouped or flat) with updated versions where upgrades were found.

## Example (grouped input)
```
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
```
- name: Update flat list
  id: appsflat
  uses: ./.github/actions/update-applications
  with:
    applications: >-
      [{"name":"app-platform-minimal","version":"2.0.19"},{"name":"app-consortia","version":"1.2.1"}]
```

## Sample follow-up usage
```
- name: Print updated
  run: echo '${{ steps.apps.outputs.updated-applications }}'
```

## SemVer handling
- Only numeric segments considered: major.minor.patch
- Non-numeric parts coerced to 0
- Pre-release ordering not implemented (enable inclusion via far-pre-release)

## Edge cases
| Scenario | Behavior |
|----------|----------|
| FAR unreachable | Application left unchanged (empty version list) |
| No versions returned | Unchanged |
| No candidate in scope | Unchanged |
| Invalid JSON input | Action fails early |
| Mixed grouping keys | All preserved and updated in-place |

## Performance
Each app triggers one FAR request (with filtering params). Batch all apps in a single action step to limit overhead.

## Local development
```
cd .github/actions/update-applications
python3 update-applications.py  # demo mode

APPLICATIONS_JSON='[{"name":"app-platform-minimal","version":"2.0.19"}]' \
FILTER_SCOPE=patch SORT_ORDER=asc python3 update-applications.py
```
Install dependencies:
```
pip install requests
```

## Troubleshooting
| Symptom | Possible Cause | Mitigation |
|---------|----------------|-----------|
| HTTP non-200 | FAR base URL incorrect / service issue | Verify far-base-url, retry |
| No updates found | Scope too narrow | Try filter-scope: minor or major |
| Timeout | Network latency | Increase request-timeout |
| Pre-releases missing | Not included | Set far-pre-release: true |

## Future enhancements
- Add caching layer for FAR responses
- Support proper pre-release precedence
- Optional changelog URL emission

## License
Inherits repository license.

