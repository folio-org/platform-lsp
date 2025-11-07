# Generate Package Diff Report

Generates a collapsed diff and formatted markdown report comparing `package.json` dependencies between base and head branches.

## Description

This action compares npm dependencies between two versions of `package.json` (typically from base and head branches) and produces:

- A JSON array of changes (package name, old version, new version)
- A formatted markdown table for PR descriptions or reports
- Change count and boolean flag

The action follows the same pattern as `generate-platform-diff-report` but focuses on npm dependencies.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `base_package_path` | Path to base package.json file | Yes | - |
| `head_package_path` | Path to head package.json file | Yes | - |
| `release_branch` | Base branch name for display in markdown | Yes | - |
| `update_branch` | Head branch name for display in markdown | Yes | - |
| `dependency_type` | Dependency type to compare (`dependencies`, `devDependencies`, `all`) | No | `dependencies` |

## Outputs

| Output | Description |
|--------|-------------|
| `ui_updates_markdown` | Formatted markdown report of dependency changes |
| `ui_updates_cnt` | Number of dependency changes detected |
| `diff_json` | JSON array of dependency changes with old/new versions |
| `has_changes` | Whether any dependency changes were detected (`true`/`false`) |

## Usage

### Basic Usage

```yaml
- name: 'Generate package diff report'
  id: package-diff
  uses: folio-org/platform-lsp/.github/actions/generate-package-diff-report@master
  with:
    base_package_path: package.json.base
    head_package_path: package.json
    release_branch: R1-2025
    update_branch: R1-2025-update
```

### Compare devDependencies

```yaml
- name: 'Generate package diff report'
  id: package-diff
  uses: folio-org/platform-lsp/.github/actions/generate-package-diff-report@master
  with:
    base_package_path: package.json.base
    head_package_path: package.json
    release_branch: R1-2025
    update_branch: R1-2025-update
    dependency_type: devDependencies
```

### Compare All Dependencies

```yaml
- name: 'Generate package diff report'
  id: package-diff
  uses: folio-org/platform-lsp/.github/actions/generate-package-diff-report@master
  with:
    base_package_path: package.json.base
    head_package_path: package.json
    release_branch: R1-2025
    update_branch: R1-2025-update
    dependency_type: all
```

### Use Outputs

```yaml
- name: 'Generate package diff report'
  id: package-diff
  uses: folio-org/platform-lsp/.github/actions/generate-package-diff-report@master
  with:
    base_package_path: package.json.base
    head_package_path: package.json
    release_branch: R1-2025
    update_branch: R1-2025-update

- name: 'Display report'
  if: steps.package-diff.outputs.has_changes == 'true'
  run: |
    echo "Found ${{ steps.package-diff.outputs.ui_updates_cnt }} changes"
    echo "${{ steps.package-diff.outputs.ui_updates_markdown }}" >> $GITHUB_STEP_SUMMARY
```

## Example Output

### Markdown Report (with changes)

```markdown
### UI Dependency Updates

**Base branch:** R1-2025
**Head branch:** R1-2025-update
**Updated dependencies:** 2

| Dependency | Old Version | New Version |
| ---------- | ----------- | ----------- |
| @folio/stripes | ^9.0.0 | ^9.1.0 |
| react | ^18.2.0 | ^18.3.0 |

> This table shows the collapsed diff of `package.json` dependencies between base and head branches.
```

### Markdown Report (no changes)

```markdown
### UI Dependency Updates

_No changes detected between base and head package.json._
```

### JSON Diff Output

```json
[
  {
    "name": "@folio/stripes",
    "change": {
      "old": "^9.0.0",
      "new": "^9.1.0"
    }
  },
  {
    "name": "react",
    "change": {
      "old": "^18.2.0",
      "new": "^18.3.0"
    }
  }
]
```

## Error Handling

- **Missing head package.json**: Exits with error (required file)
- **Missing base package.json**: Emits warning, returns empty results (graceful handling)
- **Invalid dependency_type**: Exits with error
- **Empty files**: Handled gracefully with appropriate warnings

## Implementation Notes

- Uses `jq` for JSON parsing and diff calculation
- Sorts results alphabetically by package name
- Only reports packages that changed versions (not additions or removals)
- Follows FOLIO Bash scripting standards (`set -euo pipefail`, `IFS=$'\n\t'`)
- Uses structured logging with GitHub Actions annotations

## Dependencies

- `jq` - JSON processor (pre-installed on GitHub runners)
- `bash` - Shell scripting (pre-installed on GitHub runners)

## Related Actions

- [generate-platform-diff-report](../generate-platform-diff-report/) - Compares platform descriptors
- [update-package-json](../update-package-json/) - Updates package.json dependencies
- [fetch-base-file](../fetch-base-file/) - Fetches base branch files for comparison

