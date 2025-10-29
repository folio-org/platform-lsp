# Action Extraction Report #6: build-pr-body

**Phase:** 2 (Medium Priority)  
**Complexity Reduction:** ~40 lines  
**Impact:** Low-Medium  
**Implementation Time:** 1-2 hours

---

## Overview

### Purpose
Constructs a structured pull request description from multiple markdown sections (platform updates, UI updates, missing dependencies). Creates a consistent, well-formatted PR body for automated release updates.

### Current Problem
The PR body construction logic (~40 lines) is embedded in the `manage-pr` job. While not overly complex, extracting it provides:
- Reusable PR body construction pattern
- Consistent formatting across workflows
- Easier testing of PR description logic

### Benefits of Extraction
- **Reusability:** Can be used in other PR automation workflows
- **Consistency:** Single source of truth for PR format
- **Extensibility:** Easy to add new sections or formatting
- **Testability:** Validate PR body construction independently

---

## Current Implementation

### Location in Workflow
**File:** `.github/workflows/release-update-flow.yml`  
**Job:** `manage-pr`  
**Step:** "Build collapsed PR body"

### Current Code

```yaml
- name: 'Build collapsed PR body'
  id: build-pr-body
  if: |
    needs.update-platform-descriptor.outputs.updated == 'true' ||
    needs.determine-source-branch.outputs.update_branch_exists == 'true'
  env:
    NEW_VERSION: ${{ needs.update-platform-descriptor.outputs.new_version }}
    UPDATES_CNT: ${{ needs.generate-reports.outputs.updates_cnt }}
    UPDATES_MARKDOWN: ${{ needs.generate-reports.outputs.updates_markdown }}
    UI_UPDATES_MARKDOWN: ${{ needs.generate-reports.outputs.ui_updates_markdown }}
    MISSING_UI_MARKDOWN: ${{ needs.generate-reports.outputs.missing_ui_markdown }}
    RELEASE_BRANCH: ${{ inputs.release_branch }}
    UPDATE_BRANCH: ${{ inputs.update_branch }}
  run: |
    set -euo pipefail
    IFS=$'\n\t'

    version_display="${NEW_VERSION:-No version change}"
    count_display="${UPDATES_CNT:-0}"

    # Build complete PR body with collapsed report
    pr_body=$(cat <<EOF
    ## Automated Release Update

    **Base branch:** ${RELEASE_BRANCH}
    **Head branch:** ${UPDATE_BRANCH}
    **Platform version:** ${version_display}
    **Total changes:** ${count_display}

    ---

    ${UPDATES_MARKDOWN:-### Application & Component Updates

    No applications or eureka components were updated.}

    ---

    ${UI_UPDATES_MARKDOWN:-### UI Dependency Updates

    No UI dependencies were updated.}

    ---

    ${MISSING_UI_MARKDOWN:-### Missing UI Dependencies

    No missing UI dependencies detected.}

    ---

    > This PR description is auto-generated from a collapsed diff between the base and head branches.
    > Re-running the workflow with the same base/head state produces an identical description.
    EOF
    )

    {
      echo 'pr_body<<EOF'
      echo "$pr_body"
      echo 'EOF'
    } >> "$GITHUB_OUTPUT"

    echo "::notice::Built collapsed PR body (${#pr_body} bytes)"
```

### Complexity Analysis
- **Lines:** ~40 lines
- **Dependencies:** None (pure Bash)
- **Logic:** String interpolation and formatting
- **Reusability:** Medium (pattern useful for other PR workflows)

---

## Action Specification

### Inputs

```yaml
inputs:
  version:
    description: 'Platform version for display'
    required: false
    default: 'No version change'
  
  updates_cnt:
    description: 'Number of updates'
    required: false
    default: '0'
  
  updates_markdown:
    description: 'Application & component updates markdown section'
    required: false
    default: '### Application & Component Updates\n\nNo updates detected.'
  
  ui_updates_markdown:
    description: 'UI dependency updates markdown section'
    required: false
    default: '### UI Dependency Updates\n\nNo UI dependencies were updated.'
  
  missing_ui_markdown:
    description: 'Missing UI dependencies markdown section'
    required: false
    default: '### Missing UI Dependencies\n\nNo missing UI dependencies detected.'
  
  release_branch:
    description: 'Base release branch name'
    required: true
  
  update_branch:
    description: 'Update branch name'
    required: true
  
  custom_header:
    description: 'Custom header text (optional)'
    required: false
    default: '## Automated Release Update'
  
  custom_footer:
    description: 'Custom footer text (optional)'
    required: false
    default: '> This PR description is auto-generated from a collapsed diff.'
```

### Outputs

```yaml
outputs:
  pr_body:
    description: 'Complete formatted PR body markdown'
    value: ${{ steps.build.outputs.pr_body }}
  
  pr_body_length:
    description: 'Length of PR body in bytes'
    value: ${{ steps.build.outputs.pr_body_length }}
```

---

## Implementation Guide

### Step 1: Create Action

```bash
mkdir -p .github/actions/build-pr-body
cd .github/actions/build-pr-body
```

### Step 2: Create `action.yml`

```yaml
name: 'Build PR Body'
description: 'Constructs structured PR description from markdown sections'
author: 'FOLIO DevOps'

inputs:
  version:
    description: 'Platform version'
    required: false
    default: 'No version change'
  updates_cnt:
    description: 'Number of updates'
    required: false
    default: '0'
  updates_markdown:
    description: 'Updates markdown'
    required: false
    default: '### Application & Component Updates\n\nNo updates detected.'
  ui_updates_markdown:
    description: 'UI updates markdown'
    required: false
    default: '### UI Dependency Updates\n\nNo UI dependencies were updated.'
  missing_ui_markdown:
    description: 'Missing UI markdown'
    required: false
    default: '### Missing UI Dependencies\n\nNo missing UI dependencies detected.'
  release_branch:
    description: 'Release branch'
    required: true
  update_branch:
    description: 'Update branch'
    required: true
  custom_header:
    description: 'Custom header'
    required: false
    default: '## Automated Release Update'
  custom_footer:
    description: 'Custom footer'
    required: false
    default: '> This PR description is auto-generated from a collapsed diff between the base and head branches.'

outputs:
  pr_body:
    description: 'PR body markdown'
    value: ${{ steps.build.outputs.pr_body }}
  pr_body_length:
    description: 'PR body length'
    value: ${{ steps.build.outputs.pr_body_length }}

runs:
  using: 'composite'
  steps:
    - name: 'Build PR body'
      id: build
      shell: bash
      env:
        VERSION: ${{ inputs.version }}
        UPDATES_CNT: ${{ inputs.updates_cnt }}
        UPDATES_MARKDOWN: ${{ inputs.updates_markdown }}
        UI_UPDATES_MARKDOWN: ${{ inputs.ui_updates_markdown }}
        MISSING_UI_MARKDOWN: ${{ inputs.missing_ui_markdown }}
        RELEASE_BRANCH: ${{ inputs.release_branch }}
        UPDATE_BRANCH: ${{ inputs.update_branch }}
        CUSTOM_HEADER: ${{ inputs.custom_header }}
        CUSTOM_FOOTER: ${{ inputs.custom_footer }}
      run: |
        set -euo pipefail
        IFS=$'\n\t'
        
        # Build PR body with all sections
        pr_body=$(cat <<EOF
        ${CUSTOM_HEADER}

        **Base branch:** ${RELEASE_BRANCH}
        **Head branch:** ${UPDATE_BRANCH}
        **Platform version:** ${VERSION}
        **Total changes:** ${UPDATES_CNT}

        ---

        ${UPDATES_MARKDOWN}

        ---

        ${UI_UPDATES_MARKDOWN}

        ---

        ${MISSING_UI_MARKDOWN}

        ---

        ${CUSTOM_FOOTER}
        EOF
        )
        
        pr_body_length=${#pr_body}
        
        {
          echo 'pr_body<<EOF'
          echo "$pr_body"
          echo 'EOF'
        } >> "$GITHUB_OUTPUT"
        
        echo "pr_body_length=$pr_body_length" >> "$GITHUB_OUTPUT"
        
        echo "::notice::Built PR body ($pr_body_length bytes)"
```

### Step 3: Create `README.md`

```markdown
# Build PR Body Action

Constructs a structured pull request description from multiple markdown sections.

## Usage

```yaml
- name: Build PR body
  id: pr-body
  uses: folio-org/platform-lsp/.github/actions/build-pr-body@master
  with:
    version: ${{ needs.update.outputs.new_version }}
    updates_cnt: ${{ needs.reports.outputs.updates_cnt }}
    updates_markdown: ${{ needs.reports.outputs.updates_markdown }}
    ui_updates_markdown: ${{ needs.reports.outputs.ui_updates_markdown }}
    missing_ui_markdown: ${{ needs.reports.outputs.missing_ui_markdown }}
    release_branch: R1-2025
    update_branch: R1-2025-update

- name: Use PR body
  run: echo "${{ steps.pr-body.outputs.pr_body }}"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `version` | Platform version | No | `No version change` |
| `updates_cnt` | Number of updates | No | `0` |
| `updates_markdown` | Updates section | No | Default message |
| `ui_updates_markdown` | UI updates section | No | Default message |
| `missing_ui_markdown` | Missing UI section | No | Default message |
| `release_branch` | Base branch | Yes | - |
| `update_branch` | Head branch | Yes | - |
| `custom_header` | Custom header | No | Default header |
| `custom_footer` | Custom footer | No | Default footer |

## Outputs

| Output | Description |
|--------|-------------|
| `pr_body` | Complete PR body markdown |
| `pr_body_length` | Length in bytes |

## Format

The action generates a PR body with this structure:

```
## Automated Release Update

**Base branch:** R1-2025
**Head branch:** R1-2025-update
**Platform version:** R1-2025.5
**Total changes:** 12

---

### Application & Component Updates
[Updates table]

---

### UI Dependency Updates
[UI updates table]

---

### Missing UI Dependencies
[Missing dependencies table]

---

> Auto-generated description.
```

## Customization

Override header/footer for custom PR styles:

```yaml
with:
  custom_header: '# Custom Release Update'
  custom_footer: '> Custom footer message'
```
```

### Step 4: Update Workflow

```yaml
# Before
- name: 'Build collapsed PR body'
  id: build-pr-body
  # ...~40 lines...

# After
- name: 'Build PR body'
  id: build-pr-body
  uses: folio-org/platform-lsp/.github/actions/build-pr-body@RANCHER-2324
  with:
    version: ${{ needs.update-platform-descriptor.outputs.new_version }}
    updates_cnt: ${{ needs.generate-reports.outputs.updates_cnt }}
    updates_markdown: ${{ needs.generate-reports.outputs.updates_markdown }}
    ui_updates_markdown: ${{ needs.generate-reports.outputs.ui_updates_markdown }}
    missing_ui_markdown: ${{ needs.generate-reports.outputs.missing_ui_markdown }}
    release_branch: ${{ inputs.release_branch }}
    update_branch: ${{ inputs.update_branch }}
```

---

## Testing Strategy

### Test Scenarios

1. **All sections populated** → Complete formatted PR body
2. **Minimal inputs (defaults)** → Default messages used
3. **Custom header/footer** → Custom text appears
4. **Large content** → Length correctly calculated
5. **Special characters in markdown** → Proper escaping

### Test Script

```bash
# Test with all inputs
VERSION="R1-2025.5" \
UPDATES_CNT="10" \
UPDATES_MARKDOWN="### Updates\nTest table" \
UI_UPDATES_MARKDOWN="### UI\nTest UI" \
MISSING_UI_MARKDOWN="### Missing\nNone" \
RELEASE_BRANCH="R1-2025" \
UPDATE_BRANCH="R1-2025-update" \
CUSTOM_HEADER="## Test Header" \
CUSTOM_FOOTER="> Test footer" \
bash -c 'source action-inline-script.sh'

# Verify output structure and length
```

---

## Success Criteria

- [ ] Action created with proper structure
- [ ] Handles all input combinations correctly
- [ ] Generates well-formatted markdown
- [ ] Workflow integration successful
- [ ] Output matches previous format
- [ ] Documentation complete
- [ ] Custom header/footer work

---

## Extension Ideas

Future enhancements could include:

- **Template support:** Load PR body template from file
- **Conditional sections:** Hide empty sections automatically
- **Emoji support:** Add status emojis (✅ ❌ ⚠️)
- **Link generation:** Auto-link to workflow run or issues
- **Summary stats:** Add high-level statistics section

---

**Implementation Priority:** 🟢 Low-Medium  
**Estimated Effort:** 1-2 hours  
**Dependencies:** None  
**Previous Action:** [Action #5: generate-package-diff-report](./05-generate-package-diff-report.md)  
**Completion:** This is the final action extraction

