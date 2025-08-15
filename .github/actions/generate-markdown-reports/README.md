# Generate Markdown Reports

This composite action generates collapsed markdown reports for platform updates, UI dependency changes, and missing UI modules. It processes diff report outputs and missing module data to produce formatted markdown sections suitable for PR bodies or step summaries.

## Description

The action consolidates multiple data sources (platform descriptor diffs, package.json diffs, and missing UI module reports) into three structured markdown outputs. It handles cases where no updates are detected and provides fallback content. The action also supports writing reports directly to the GitHub step summary for visibility in the Actions UI.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `updated` | Whether updates were detected (true/false) | Yes | - |
| `failure_reason` | Failure reason if no updates detected | No | `''` |
| `descriptor_markdown` | Markdown content from platform descriptor diff report | No | `''` |
| `ui_updates_markdown` | Markdown content from package diff report | No | `''` |
| `not_found_ui_report` | JSON object with missing UI modules (module name -> version) | No | `'{}'` |
| `package_diff_available` | Whether package diff report is available (true/false) | No | `'false'` |
| `write_to_summary` | Whether to write reports to GitHub step summary | No | `'true'` |

## Outputs

| Output | Description |
|--------|-------------|
| `updates_markdown` | Formatted markdown for application & component updates |
| `ui_updates_markdown` | Formatted markdown for UI dependency updates |
| `missing_ui_markdown` | Formatted markdown for missing UI dependencies |

## Usage

### Basic Example

```yaml
- name: 'Generate markdown reports'
  id: generate-reports
  uses: folio-org/platform-lsp/.github/actions/generate-markdown-reports@master
  with:
    updated: 'true'
    descriptor_markdown: ${{ steps.build-change-report.outputs.updates_markdown }}
    ui_updates_markdown: ${{ steps.build-ui-diff.outputs.ui_updates_markdown }}
    not_found_ui_report: ${{ needs.update-package-json.outputs.not_found_ui_report }}
    package_diff_available: 'true'
    write_to_summary: 'true'

- name: 'Use generated reports'
  run: |
    echo "Updates: ${{ steps.generate-reports.outputs.updates_markdown }}"
    echo "UI Updates: ${{ steps.generate-reports.outputs.ui_updates_markdown }}"
    echo "Missing: ${{ steps.generate-reports.outputs.missing_ui_markdown }}"
```

### No Updates Detected

```yaml
- name: 'Generate reports for failed update'
  id: generate-reports
  uses: folio-org/platform-lsp/.github/actions/generate-markdown-reports@master
  with:
    updated: 'false'
    failure_reason: 'No new versions available for configured modules'
    write_to_summary: 'true'
```

### Integration with PR Body Builder

```yaml
- name: 'Generate markdown reports'
  id: generate-reports
  uses: folio-org/platform-lsp/.github/actions/generate-markdown-reports@master
  with:
    updated: ${{ needs.update-platform-descriptor.outputs.updated }}
    failure_reason: ${{ needs.update-platform-descriptor.outputs.failure_reason }}
    descriptor_markdown: ${{ steps.build-change-report.outputs.updates_markdown }}
    ui_updates_markdown: ${{ steps.build-ui-diff.outputs.ui_updates_markdown }}
    not_found_ui_report: ${{ needs.update-package-json.outputs.not_found_ui_report }}
    package_diff_available: ${{ steps.build-ui-diff.outputs.has_changes != '' && 'true' || 'false' }}

- name: 'Build PR body'
  id: build-pr-body
  uses: folio-org/platform-lsp/.github/actions/build-pr-body@master
  with:
    new_version: ${{ needs.update-platform-descriptor.outputs.new_version }}
    updates_cnt: ${{ needs.generate-reports.outputs.updates_cnt }}
    updates_markdown: ${{ steps.generate-reports.outputs.updates_markdown }}
    ui_updates_markdown: ${{ steps.generate-reports.outputs.ui_updates_markdown }}
    missing_ui_markdown: ${{ steps.generate-reports.outputs.missing_ui_markdown }}
    release_branch: ${{ inputs.release_branch }}
    update_branch: ${{ inputs.update_branch }}
```

## Behavior

### When `updated` is `'false'`

- **Application & Component Updates**: Shows "No updates detected." or the provided `failure_reason`
- **UI Dependency Updates**: Shows "No UI dependencies were updated."
- **Missing UI Dependencies**: Shows "No missing UI dependencies detected."

### When `updated` is `'true'`

- **Application & Component Updates**: Uses the provided `descriptor_markdown` content
- **UI Dependency Updates**: 
  - If `package_diff_available` is `'true'`: Uses the provided `ui_updates_markdown`
  - Otherwise: Shows "_No package.json comparison available._"
- **Missing UI Dependencies**:
  - If `not_found_ui_report` is empty or `'{}'`: Shows "No missing UI dependencies detected."
  - Otherwise: Renders a table with module names and versions, along with count and description

### Missing UI Modules Table Format

When missing UI modules are detected, the output includes:

```markdown
### Missing UI Dependencies

**Missing entries:** {count}

| Module | Referenced Version |
| ------ | ------------------ |
| @folio/example-module | 1.2.3 |
| @folio/another-module | 2.0.0 |

> These UI modules are referenced by application descriptors but were NOT found in `package.json`.
```

### GitHub Step Summary

When `write_to_summary` is `'true'` (default), all three markdown sections are automatically appended to `$GITHUB_STEP_SUMMARY`, making them visible in the GitHub Actions UI under the job summary.

## Implementation Notes

- **Shell Safety**: Uses `set -euo pipefail` and `IFS=$'\n\t'` for safe Bash execution
- **JSON Validation**: Validates JSON input with `jq` before processing
- **Multiline Output**: Uses heredoc syntax (`EOF`) for clean multiline output handling
- **Fallback Logic**: Provides sensible defaults for all missing or empty inputs
- **Single Responsibility**: Focuses solely on report generation; does not fetch data or make decisions about updates

## Dependencies

- **jq**: Required for JSON parsing and manipulation

## See Also

- [generate-platform-diff-report](../generate-platform-diff-report/README.md) - Generates platform descriptor diffs
- [generate-package-diff-report](../generate-package-diff-report/README.md) - Generates package.json diffs
- [build-pr-body](../build-pr-body/README.md) - Builds complete PR body from markdown reports
- [update-package-json](../update-package-json/README.md) - Updates package.json and reports missing modules

