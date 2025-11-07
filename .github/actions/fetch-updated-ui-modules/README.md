# Fetch Updated UI Modules Action

Fetch UI modules from FOLIO application descriptors using the FAR API.

## Purpose
Given a set of application name/version pairs (either a flat array or an object containing `required` and/or `optional` arrays), this action retrieves each application's descriptor from FAR and aggregates all `uiModules` entries, exposing them as outputs for downstream workflow steps.

Business logic is unchanged; this README documents current behavior.

## Inputs

| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `applications` | yes | n/a | JSON string representing application objects. Accepts either an array of objects (`[{"name":"ui-inventory","version":"10.0.0"}, ...]`) or an object with `required` / `optional` arrays: `{ "required": [...], "optional": [...] }`. |
| `far-url` | no | `https://far.ci.folio.org` | Base URL for FAR API. |

## Outputs

| Name | Description |
|------|-------------|
| `ui-modules` | JSON array of collected `uiModules` objects across all applications. |
| `ui-modules-count` | Numeric count of collected UI modules. |

## Example Usage

```yaml
jobs:
  collect-ui-modules:
    runs-on: ubuntu-latest
    steps:
      - uses: folio-org/platform-lsp/.github/actions/fetch-updated-ui-modules@main
        id: fetch
        with:
          applications: >-
            {"required": [
              {"name": "ui-inventory", "version": "10.0.0"},
              {"name": "ui-users", "version": "9.2.0"}
            ], "optional": [
              {"name": "ui-calendar", "version": "2.1.0"}
            ]}
      - name: Show results
        run: |
          echo "Count: ${{ steps.fetch.outputs.ui-modules-count }}"
          echo "Modules JSON: ${{ steps.fetch.outputs.ui-modules }}"
```

## How It Works
1. The composite action sets up Python.
2. The Python script fetches each application descriptor concurrently (up to 5 workers).
3. All `uiModules` arrays found are flattened into a single list.
4. Outputs are written to a temporary JSON file and then extracted using `jq` for GitHub Action outputs.

## Error Handling
- Failed descriptor fetches are logged as `::warning::` and skipped.
- Malformed input JSON or missing file paths emit `::error::` and cause exit.
- Missing output file creation results in an `::error::` and step failure.

## Local Testing
You can run the Python script directly for ad-hoc checks:

```bash
python3 fetch-updated-ui-modules.py \
  --api-url https://far.ci.folio.org \
  --modules '{"required": [{"name": "ui-inventory", "version": "10.0.0"}]}'
```

## Implementation Notes
- Network concurrency uses `ThreadPoolExecutor` with a default of 5 workers.
- A unified helper `_flatten_modules_structure` normalizes input formats.
- Business logic intentionally preserved; only structural and documentation improvements were made.

## License
Uses the repository license.

