# Update Package JSON Dependencies Action

Composite GitHub Action that updates `package.json` dependencies using an input list of UI modules (each containing a `name` and `version`). Only upgrades are applied (never downgrades); dependencies not already present are reported but not added.

## Inputs

| Name | Description | Required |
|------|-------------|----------|
| `package-json` | Full `package.json` content as a JSON string | yes |
| `ui-modules` | JSON string of an array of objects: `[{"name": "folio_some-module", "version": "x.y.z"}, ...]` | yes |
| `ignore-not-found` | JSON array of module names to exclude from `not-found-ui-report` (e.g., `["folio_stripes-core", "folio_stripes-smart-components"]`) | no (default: `[]`) |

## Outputs

| Name | Description |
|------|-------------|
| `package-json` | Updated `package.json` content (stringified JSON) |
| `updated-ui-report` | Array of updated modules with `{name, change: {old, new}}` |
| `not-found-ui-report` | Object map of modules not found in existing dependencies |
| `updated-count` | Number of dependencies updated |
| `has-updates` | `true` if any dependency was updated, otherwise `false` |

## Behavior

1. Module names starting with `folio_` are converted to scoped `@folio/` names.
2. A dependency is updated only if:
   - It already exists in `package.json.dependencies`.
   - Its current value is an exact version (`X.Y.Z`, optionally with a pre-release suffix).
   - The new version is strictly higher (numeric comparison of dotted segments; non-digit characters ignored except leading `v^~`).
3. Equal or lower versions are ignored (skipped with log message).
4. A range constraint (`>=1.0.0`, `^1.0.0`, `~1.0.0`, comparators joined by spaces, alternatives by `||`) is never rewritten — yarn resolves it. The new module version must satisfy it: if it does not, or the constraint syntax is not supported, the violation is reported with `::error::` and the action exits `1` after writing its results. The operator fixes the constraint in `package.json`.
5. Missing dependencies are collected in `not-found-ui-report` but never added, unless they are in the `ignore-not-found` list.
6. Modules in the `ignore-not-found` list are still skipped if not found, but excluded from the `not-found-ui-report` output.
7. Exit code is `0` whether or not anything was updated; only a constraint violation makes it `1`.

## Example Usage

```yaml
jobs:
  update-deps:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Read package.json
        id: pkg
        run: |
          content=$(cat package.json | jq -c '.')
          echo "content=$content" >> $GITHUB_OUTPUT

      - name: Provide UI modules list
        id: modules
        run: |
          ui_modules='[{"name":"folio_users","version":"9.1.0"},{"name":"folio_inventory","version":"6.2.0"}]'
          echo "list=$ui_modules" >> $GITHUB_OUTPUT

      - name: Update dependencies
        id: update
        uses: ./.github/actions/update-package-json
        with:
          package-json: ${{ steps.pkg.outputs.content }}
          ui-modules: ${{ steps.modules.outputs.list }}
          ignore-not-found: '["folio_stripes-core", "folio_stripes-smart-components"]'

      - name: Show summary
        run: |
          echo "Updated count: ${{ steps.update.outputs.updated-count }}"
          echo "Has updates: ${{ steps.update.outputs.has-updates }}"
          echo "Updated modules: ${{ steps.update.outputs.updated-ui-report }}"
          echo "Not found modules: ${{ steps.update.outputs.not-found-ui-report }}"
```

## Internal Script Notes

`update-package-json.py` is intentionally simple:
- Uses functional helpers with type hints.
- Avoids altering business logic: only eligible upgrades applied.
- Prints informative messages consumed by workflow logs.
- Produces a structured JSON file parsed by the composite step.

## Maintenance Tips

- Upgrade `actions/setup-python` to `@v5` once broadly stable in the ecosystem.
- Ensure input JSON strings are compact (single line) to avoid YAML quoting issues.
- When adding new logic, preserve current upgrade/downgrade rules unless intentionally changing business behavior.

## Changelog (Refactor)

- Added type hints and improved docstrings in Python script.
- Removed raw input echo to avoid verbose logs.
- Added bash safety (`set -euo pipefail`) in composite step.
- Clarified comments and descriptions in `action.yml`.
- Created this README for usage transparency.

