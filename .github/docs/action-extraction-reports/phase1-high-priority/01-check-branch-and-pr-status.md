# Action Extraction Report #1: check-branch-and-pr-status

**Phase:** 1 (High Priority)  
**Complexity Reduction:** ~40 lines  
**Impact:** High  
**Implementation Time:** 2-3 hours

---

## Overview

### Purpose
Determines which branch to scan for updates and checks whether a pull request already exists between the update branch and release branch. This is a critical workflow precondition that affects all downstream jobs.

### Current Problem
The logic is embedded in the workflow's first job (`determine-source-branch`) as two separate steps with ~40 lines of inline Bash scripting. This makes it:
- Hard to test independently
- Not reusable in other workflows
- Mixed with workflow orchestration logic

### Benefits of Extraction
- **Single Responsibility:** One action performs one logical operation
- **Reusability:** Can be used in any release or update workflow
- **Testability:** Can be tested with mock inputs
- **Maintainability:** Centralized logic easier to update

---

## Current Implementation

### Location in Workflow
**File:** `.github/workflows/release-update-flow.yml`  
**Job:** `determine-source-branch`  
**Steps:** 1-2

### Current Code

```yaml
determine-source-branch:
  name: 'Determine Source Branch and PR Status'
  runs-on: ubuntu-latest
  permissions:
    contents: read
    pull-requests: read
  outputs:
    source_branch: ${{ steps.determine-branch.outputs.source_branch }}
    update_branch_exists: ${{ steps.determine-branch.outputs.update_branch_exists }}
    pr_exists: ${{ steps.check-pr.outputs.pr_exists }}
    pr_number: ${{ steps.check-pr.outputs.pr_number }}
    pr_url: ${{ steps.check-pr.outputs.pr_url }}
  steps:
    - name: 'Determine which branch to scan'
      id: determine-branch
      env:
        REPO: ${{ inputs.repo }}
        RELEASE_BRANCH: ${{ inputs.release_branch }}
        UPDATE_BRANCH: ${{ inputs.update_branch }}
      run: |
        set -euo pipefail
        IFS=$'\n\t'
        echo "::notice::Checking if update branch exists: $UPDATE_BRANCH"
        if gh api "repos/$REPO/branches/$UPDATE_BRANCH" >/dev/null 2>&1; then
          echo "::notice::Update branch exists, will scan: $UPDATE_BRANCH"
          echo "source_branch=$UPDATE_BRANCH" >> "$GITHUB_OUTPUT"
          echo "update_branch_exists=true" >> "$GITHUB_OUTPUT"
        else
          echo "::notice::Update branch does not exist, will scan: $RELEASE_BRANCH"
          echo "source_branch=$RELEASE_BRANCH" >> "$GITHUB_OUTPUT"
          echo "update_branch_exists=false" >> "$GITHUB_OUTPUT"
        fi

    - name: 'Check for existing PR'
      id: check-pr
      if: steps.determine-branch.outputs.update_branch_exists == 'true'
      env:
        REPO: ${{ inputs.repo }}
        BASE_BRANCH: ${{ inputs.release_branch }}
        HEAD_BRANCH: ${{ inputs.update_branch }}
      run: |
        set -euo pipefail
        IFS=$'\n\t'
        echo "::notice::Checking for existing PR from $HEAD_BRANCH to $BASE_BRANCH"
        pr_json=$(gh pr list \
          --repo "$REPO" \
          --base "$BASE_BRANCH" \
          --head "$HEAD_BRANCH" \
          --json number,url \
          --jq '.[0]' || echo '{}')
        if [ "$pr_json" != "{}" ] && [ -n "$pr_json" ] && [ "$(echo "$pr_json" | jq -r '.url // ""')" != "" ]; then
          pr_number=$(echo "$pr_json" | jq -r '.number // ""')
          pr_url=$(echo "$pr_json" | jq -r '.url // ""')
          echo "::notice::Found existing PR #$pr_number: $pr_url"
          echo "pr_exists=true" >> "$GITHUB_OUTPUT"
          echo "pr_number=$pr_number" >> "$GITHUB_OUTPUT"
          echo "pr_url=$pr_url" >> "$GITHUB_OUTPUT"
        else
          echo "::notice::No existing PR found"
          echo "pr_exists=false" >> "$GITHUB_OUTPUT"
          echo "pr_number=" >> "$GITHUB_OUTPUT"
          echo "pr_url=" >> "$GITHUB_OUTPUT"
        fi
```

### Complexity Analysis
- **Lines of code:** ~40 lines across 2 steps
- **Dependencies:** `gh` CLI, `jq`
- **API calls:** 2 (branch check, PR list)
- **Conditional logic:** Branch existence check, PR parsing
- **Error handling:** Basic with stderr redirection

---

## Action Specification

### Action Metadata

```yaml
name: 'Check Branch and PR Status'
description: 'Determines source branch and checks for existing pull request'
author: 'FOLIO DevOps'

branding:
  icon: 'git-branch'
  color: 'blue'
```

### Inputs

```yaml
inputs:
  repo:
    description: 'Repository in org/repo format'
    required: true
    type: string
  
  release_branch:
    description: 'Base release branch name'
    required: true
    type: string
  
  update_branch:
    description: 'Update branch name to check'
    required: true
    type: string
  
  github_token:
    description: 'GitHub token for API access'
    required: false
    default: ${{ github.token }}
```

### Outputs

```yaml
outputs:
  source_branch:
    description: 'Branch to scan (update_branch if exists, else release_branch)'
    value: ${{ steps.check.outputs.source_branch }}
  
  update_branch_exists:
    description: 'Whether the update branch exists (true/false)'
    value: ${{ steps.check.outputs.update_branch_exists }}
  
  pr_exists:
    description: 'Whether a PR exists from update_branch to release_branch (true/false)'
    value: ${{ steps.check.outputs.pr_exists }}
  
  pr_number:
    description: 'PR number if found, empty string otherwise'
    value: ${{ steps.check.outputs.pr_number }}
  
  pr_url:
    description: 'PR URL if found, empty string otherwise'
    value: ${{ steps.check.outputs.pr_url }}
```

---

## Implementation Guide

### Step 1: Create Action Directory

```bash
mkdir -p .github/actions/check-branch-and-pr-status
cd .github/actions/check-branch-and-pr-status
```

### Step 2: Create `action.yml`

```yaml
name: 'Check Branch and PR Status'
description: 'Determines source branch and checks for existing pull request'
author: 'FOLIO DevOps'

inputs:
  repo:
    description: 'Repository in org/repo format'
    required: true
  release_branch:
    description: 'Base release branch name'
    required: true
  update_branch:
    description: 'Update branch name to check'
    required: true
  github_token:
    description: 'GitHub token for API access'
    required: false
    default: ${{ github.token }}

outputs:
  source_branch:
    description: 'Branch to scan (update_branch if exists, else release_branch)'
    value: ${{ steps.check.outputs.source_branch }}
  update_branch_exists:
    description: 'Whether the update branch exists'
    value: ${{ steps.check.outputs.update_branch_exists }}
  pr_exists:
    description: 'Whether a PR exists'
    value: ${{ steps.check.outputs.pr_exists }}
  pr_number:
    description: 'PR number if found'
    value: ${{ steps.check.outputs.pr_number }}
  pr_url:
    description: 'PR URL if found'
    value: ${{ steps.check.outputs.pr_url }}

runs:
  using: 'composite'
  steps:
    - name: 'Check branch and PR status'
      id: check
      shell: bash
      env:
        GH_TOKEN: ${{ inputs.github_token }}
        REPO: ${{ inputs.repo }}
        RELEASE_BRANCH: ${{ inputs.release_branch }}
        UPDATE_BRANCH: ${{ inputs.update_branch }}
      run: |
        set -euo pipefail
        IFS=$'\n\t'
        
        # Check if update branch exists
        echo "::notice::Checking if update branch exists: $UPDATE_BRANCH"
        if gh api "repos/$REPO/branches/$UPDATE_BRANCH" >/dev/null 2>&1; then
          echo "::notice::Update branch exists, will scan: $UPDATE_BRANCH"
          echo "source_branch=$UPDATE_BRANCH" >> "$GITHUB_OUTPUT"
          echo "update_branch_exists=true" >> "$GITHUB_OUTPUT"
          
          # Check for existing PR
          echo "::notice::Checking for existing PR from $UPDATE_BRANCH to $RELEASE_BRANCH"
          pr_json=$(gh pr list \
            --repo "$REPO" \
            --base "$RELEASE_BRANCH" \
            --head "$UPDATE_BRANCH" \
            --json number,url \
            --jq '.[0]' || echo '{}')
          
          if [ "$pr_json" != "{}" ] && [ -n "$pr_json" ] && [ "$(echo "$pr_json" | jq -r '.url // ""')" != "" ]; then
            pr_number=$(echo "$pr_json" | jq -r '.number // ""')
            pr_url=$(echo "$pr_json" | jq -r '.url // ""')
            echo "::notice::Found existing PR #$pr_number: $pr_url"
            echo "pr_exists=true" >> "$GITHUB_OUTPUT"
            echo "pr_number=$pr_number" >> "$GITHUB_OUTPUT"
            echo "pr_url=$pr_url" >> "$GITHUB_OUTPUT"
          else
            echo "::notice::No existing PR found"
            echo "pr_exists=false" >> "$GITHUB_OUTPUT"
            echo "pr_number=" >> "$GITHUB_OUTPUT"
            echo "pr_url=" >> "$GITHUB_OUTPUT"
          fi
        else
          echo "::notice::Update branch does not exist, will scan: $RELEASE_BRANCH"
          echo "source_branch=$RELEASE_BRANCH" >> "$GITHUB_OUTPUT"
          echo "update_branch_exists=false" >> "$GITHUB_OUTPUT"
          echo "pr_exists=false" >> "$GITHUB_OUTPUT"
          echo "pr_number=" >> "$GITHUB_OUTPUT"
          echo "pr_url=" >> "$GITHUB_OUTPUT"
        fi
```

### Step 3: Create `README.md`

```markdown
# Check Branch and PR Status Action

Determines which branch to scan and checks for existing pull request status.

## Usage

```yaml
- name: Check branch and PR status
  id: check-status
  uses: folio-org/platform-lsp/.github/actions/check-branch-and-pr-status@master
  with:
    repo: ${{ github.repository }}
    release_branch: 'R1-2025'
    update_branch: 'R1-2025-update'
    github_token: ${{ secrets.GITHUB_TOKEN }}

- name: Use outputs
  run: |
    echo "Source branch: ${{ steps.check-status.outputs.source_branch }}"
    echo "Update branch exists: ${{ steps.check-status.outputs.update_branch_exists }}"
    echo "PR exists: ${{ steps.check-status.outputs.pr_exists }}"
    echo "PR number: ${{ steps.check-status.outputs.pr_number }}"
    echo "PR URL: ${{ steps.check-status.outputs.pr_url }}"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `repo` | Repository in org/repo format | Yes | - |
| `release_branch` | Base release branch name | Yes | - |
| `update_branch` | Update branch to check | Yes | - |
| `github_token` | GitHub token for API access | No | `${{ github.token }}` |

## Outputs

| Output | Description | Example |
|--------|-------------|---------|
| `source_branch` | Branch to scan | `R1-2025-update` or `R1-2025` |
| `update_branch_exists` | Whether update branch exists | `true` or `false` |
| `pr_exists` | Whether PR exists | `true` or `false` |
| `pr_number` | PR number if found | `123` or `` |
| `pr_url` | PR URL if found | `https://github.com/...` or `` |

## Logic

1. **Check Update Branch:** Uses GitHub API to check if update_branch exists
2. **Determine Source:** If update_branch exists, use it; otherwise use release_branch
3. **Check PR:** If update_branch exists, search for PR from update_branch to release_branch
4. **Return Status:** Output all status information for downstream jobs

## Requirements

- GitHub CLI (`gh`) available in runner
- `jq` for JSON parsing
- Token with `contents:read` and `pull-requests:read` permissions
```

### Step 4: Update Workflow

Replace the `determine-source-branch` job steps with:

```yaml
determine-source-branch:
  name: 'Determine Source Branch and PR Status'
  runs-on: ubuntu-latest
  permissions:
    contents: read
    pull-requests: read
  outputs:
    source_branch: ${{ steps.check-status.outputs.source_branch }}
    update_branch_exists: ${{ steps.check-status.outputs.update_branch_exists }}
    pr_exists: ${{ steps.check-status.outputs.pr_exists }}
    pr_number: ${{ steps.check-status.outputs.pr_number }}
    pr_url: ${{ steps.check-status.outputs.pr_url }}
  steps:
    - name: 'Check branch and PR status'
      id: check-status
      uses: folio-org/platform-lsp/.github/actions/check-branch-and-pr-status@RANCHER-2324
      with:
        repo: ${{ inputs.repo }}
        release_branch: ${{ inputs.release_branch }}
        update_branch: ${{ inputs.update_branch }}
        github_token: ${{ secrets.GITHUB_TOKEN }}
```

---

## Testing Strategy

### Test Scenarios

1. **Update branch exists, PR exists**
   - Input: Existing update branch with open PR
   - Expected: source_branch=update_branch, update_branch_exists=true, pr_exists=true, pr_number and pr_url populated

2. **Update branch exists, no PR**
   - Input: Existing update branch, no PR
   - Expected: source_branch=update_branch, update_branch_exists=true, pr_exists=false, pr_number and pr_url empty

3. **Update branch does not exist**
   - Input: Non-existent update branch
   - Expected: source_branch=release_branch, update_branch_exists=false, pr_exists=false, pr_number and pr_url empty

4. **API failure handling**
   - Input: Invalid repo or insufficient permissions
   - Expected: Appropriate error message, workflow fails gracefully

### Manual Testing

```bash
# Test locally with act or in a test workflow
.github/workflows/test-check-branch-and-pr-status.yml
```

### Test Workflow Example

```yaml
name: Test Check Branch and PR Status
on: workflow_dispatch

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Test action
        id: test
        uses: ./.github/actions/check-branch-and-pr-status
        with:
          repo: folio-org/platform-lsp
          release_branch: R1-2025
          update_branch: R1-2025-update
      
      - name: Validate outputs
        run: |
          echo "Source: ${{ steps.test.outputs.source_branch }}"
          echo "Branch exists: ${{ steps.test.outputs.update_branch_exists }}"
          echo "PR exists: ${{ steps.test.outputs.pr_exists }}"
```

---

## Success Criteria

- [ ] Action directory created with proper structure
- [ ] `action.yml` implements all specified inputs/outputs
- [ ] `README.md` documents usage with examples
- [ ] Workflow updated to use new action
- [ ] All test scenarios pass
- [ ] No regression in workflow functionality
- [ ] Action is reusable in other workflows
- [ ] Code follows FOLIO safe shell practices

---

## Integration Checklist

- [ ] Create action files (action.yml, README.md)
- [ ] Test action independently
- [ ] Update workflow to use action
- [ ] Run workflow with dry_run=true
- [ ] Verify outputs match previous behavior
- [ ] Run workflow in production
- [ ] Document action in main README
- [ ] Tag action version if needed

---

**Implementation Priority:** 🔴 High  
**Estimated Effort:** 2-3 hours  
**Dependencies:** None  
**Next Action:** [Action #2: fetch-base-file](./02-fetch-base-file.md)

