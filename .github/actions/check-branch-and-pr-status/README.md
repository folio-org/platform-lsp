# Check Branch and PR Status Action

Determines which branch to scan for updates and checks for existing pull request status between the update branch and release branch.

## Overview

This composite action encapsulates the logic for determining the source branch to scan and checking whether a pull request already exists. It is a critical precondition step that affects downstream workflow jobs.

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
    if [ "${{ steps.check-status.outputs.pr_exists }}" = "true" ]; then
      echo "PR #${{ steps.check-status.outputs.pr_number }}: ${{ steps.check-status.outputs.pr_url }}"
    fi
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `repo` | Repository in org/repo format | Yes | - |
| `release_branch` | Base release branch name (e.g., R1-2025) | Yes | - |
| `update_branch` | Update branch name to check (e.g., R1-2025-update) | Yes | - |
| `github_token` | GitHub token for API access | No | `${{ github.token }}` |

## Outputs

| Output | Description | Example Value |
|--------|-------------|---------------|
| `source_branch` | Branch to scan for updates | `R1-2025-update` or `R1-2025` |
| `update_branch_exists` | Whether the update branch exists | `true` or `false` |
| `pr_exists` | Whether a PR exists from update_branch to release_branch | `true` or `false` |
| `pr_number` | PR number if found, empty string otherwise | `123` or `` |
| `pr_url` | PR URL if found, empty string otherwise | `https://github.com/org/repo/pull/123` or `` |

## Logic Flow

1. **Check Update Branch:** Uses GitHub API to determine if the `update_branch` exists in the repository
2. **Determine Source Branch:**
   - If `update_branch` exists → use it as `source_branch`
   - If `update_branch` does not exist → use `release_branch` as `source_branch`
3. **Check for PR:** If `update_branch` exists, search for an open PR from `update_branch` to `release_branch`
4. **Return Status:** Output all status information for use by downstream jobs

## Requirements

- **GitHub CLI (`gh`)**: Must be available in the runner environment
- **`jq`**: Required for JSON parsing
- **Permissions**: Token must have:
  - `contents: read` - to check branch existence
  - `pull-requests: read` - to list pull requests

## Example Scenarios

### Scenario 1: Update branch exists with open PR

**Input:**
- `update_branch`: `R1-2025-update` (exists)
- `release_branch`: `R1-2025`
- PR #123 is open from `R1-2025-update` to `R1-2025`

**Output:**
- `source_branch`: `R1-2025-update`
- `update_branch_exists`: `true`
- `pr_exists`: `true`
- `pr_number`: `123`
- `pr_url`: `https://github.com/org/repo/pull/123`

### Scenario 2: Update branch exists, no PR

**Input:**
- `update_branch`: `R1-2025-update` (exists)
- `release_branch`: `R1-2025`
- No open PR

**Output:**
- `source_branch`: `R1-2025-update`
- `update_branch_exists`: `true`
- `pr_exists`: `false`
- `pr_number`: `` (empty)
- `pr_url`: `` (empty)

### Scenario 3: Update branch does not exist

**Input:**
- `update_branch`: `R1-2025-update` (does not exist)
- `release_branch`: `R1-2025`

**Output:**
- `source_branch`: `R1-2025`
- `update_branch_exists`: `false`
- `pr_exists`: `false`
- `pr_number`: `` (empty)
- `pr_url`: `` (empty)

## Integration in Workflows

### In release-update-flow.yml

```yaml
jobs:
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
        uses: folio-org/platform-lsp/.github/actions/check-branch-and-pr-status@master
        with:
          repo: ${{ inputs.repo }}
          release_branch: ${{ inputs.release_branch }}
          update_branch: ${{ inputs.update_branch }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Error Handling

The action uses `set -euo pipefail` for strict error handling:
- If the GitHub API call fails unexpectedly, the action will fail
- If `gh` CLI is not available, the action will fail
- If `jq` is not available, the action will fail
- API rate limit errors will cause the action to fail

All errors are reported through standard GitHub Actions error annotations.

## Benefits of This Action

- **Single Responsibility:** Performs one logical operation (check branch and PR status)
- **Reusability:** Can be used in any workflow that needs to check branch and PR status
- **Testability:** Can be tested independently with different inputs
- **Maintainability:** Centralized logic is easier to update and maintain
- **Clarity:** Reduces workflow complexity by ~40 lines of inline scripting

## Related Actions

- `fetch-base-file`: Fetches a file from a base branch for comparison
- `generate-platform-diff-report`: Generates a diff report between platform versions

## Author

FOLIO DevOps Team

