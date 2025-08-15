# Build PR Body

This composite action builds a formatted PR body with collapsed diff reports for platform updates. It is used in the release update workflow to generate consistent PR descriptions.

## Description

The action takes markdown content for various update categories (applications/components, UI dependencies, missing dependencies) and combines them into a single formatted PR body. The output is designed to provide a clear, structured summary of all changes in the platform release update.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `new_version` | New platform version (or empty if no version change) | No | `''` |
| `updates_cnt` | Total count of updates | No | `'0'` |
| `updates_markdown` | Markdown content for application & component updates | No | `''` |
| `ui_updates_markdown` | Markdown content for UI dependency updates | No | `''` |
| `missing_ui_markdown` | Markdown content for missing UI dependencies | No | `''` |
| `release_branch` | Base/release branch name | Yes | - |
| `update_branch` | Head/update branch name | Yes | - |

## Outputs

| Output | Description |
|--------|-------------|
| `pr_body` | Formatted PR body with all sections and collapsed reports |

## Usage

### Basic Example

```yaml
- name: 'Build PR body'
  id: build-pr-body
  uses: folio-org/platform-lsp/.github/actions/build-pr-body@master
  with:
    new_version: 'R1-2025.3'
    updates_cnt: '15'
    updates_markdown: ${{ steps.generate-reports.outputs.updates_markdown }}
    ui_updates_markdown: ${{ steps.generate-reports.outputs.ui_updates_markdown }}
    missing_ui_markdown: ${{ steps.generate-reports.outputs.missing_ui_markdown }}
    release_branch: 'R1-2025'
    update_branch: 'R1-2025-update'

- name: 'Use PR body'
  run: |
    echo "${{ steps.build-pr-body.outputs.pr_body }}" > pr-body.txt
```

### Integration with PR Creation

```yaml
- name: 'Build PR body'
  id: build-pr-body
  uses: folio-org/platform-lsp/.github/actions/build-pr-body@master
  with:
    new_version: ${{ needs.update-platform.outputs.new_version }}
    updates_cnt: ${{ needs.generate-reports.outputs.updates_cnt }}
    updates_markdown: ${{ needs.generate-reports.outputs.updates_markdown }}
    ui_updates_markdown: ${{ needs.generate-reports.outputs.ui_updates_markdown }}
    missing_ui_markdown: ${{ needs.generate-reports.outputs.missing_ui_markdown }}
    release_branch: ${{ inputs.release_branch }}
    update_branch: ${{ inputs.update_branch }}

- name: 'Create PR'
  uses: folio-org/kitfox-github/.github/actions/create-pr@master
  with:
    repo: ${{ inputs.repo }}
    base_branch: ${{ inputs.release_branch }}
    head_branch: ${{ inputs.update_branch }}
    pr_title: "Release: Update to ${{ needs.update-platform.outputs.new_version }}"
    pr_body: ${{ steps.build-pr-body.outputs.pr_body }}
    pr_labels: ${{ inputs.pr_labels }}
    pr_reviewers: ${{ inputs.pr_reviewers }}
```

## Behavior

### Default Fallback Content

If any markdown input is empty, the action provides sensible defaults:
- **Empty `updates_markdown`**: "No applications or eureka components were updated."
- **Empty `ui_updates_markdown`**: "No UI dependencies were updated."
- **Empty `missing_ui_markdown`**: "No missing UI dependencies detected."

### Output Format

The PR body follows this structure:

```markdown
## Automated Release Update

**Base branch:** {release_branch}
**Head branch:** {update_branch}
**Platform version:** {new_version or "No version change"}
**Total changes:** {updates_cnt}

---

{updates_markdown or default}

---

{ui_updates_markdown or default}

---

{missing_ui_markdown or default}

---

> This PR description is auto-generated from a collapsed diff between the base and head branches.
> Re-running the workflow with the same base/head state produces an identical description.
```

## Design Principles

- **Single Responsibility**: The action focuses solely on formatting PR body content
- **Consistency**: Produces identical output for identical inputs
- **Safe Defaults**: Handles missing/empty inputs gracefully with fallback content
- **Transparency**: Includes metadata about base/head branches and version

## Related Actions

- `generate-platform-diff-report` - Generates application/component update markdown
- `generate-package-diff-report` - Generates UI dependency update markdown
- `update-package-json` - Tracks missing UI dependencies

