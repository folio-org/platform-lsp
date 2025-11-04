# Toggle App Workflow

**Workflow**: `toggle-app-workflow.yml`
**Purpose**: Enable or disable specific workflows across multiple application repositories in bulk
**Type**: Platform-level management workflow

## 🎯 Overview

This workflow provides centralized control for managing workflow states (enabled/disabled) across multiple FOLIO application repositories. It supports two operational modes: automatically discovering applications from a platform descriptor branch, or processing an explicit user-provided list of applications. The workflow executes in parallel with comprehensive result tracking and reporting, making it ideal for scheduled maintenance, emergency response, or coordinated workflow management across the platform.

## 📋 Workflow Interface

### Inputs

| Input              | Description                                                          | Required     | Type    | Default |
|--------------------|----------------------------------------------------------------------|--------------|---------|---------|
| `source_type`      | Source of application list: `platform-descriptor` or `explicit-list` | Yes          | choice  | -       |
| `platform_branch`  | Platform branch to get app list from (e.g., snapshot, R1-2025)       | Conditional* | string  | -       |
| `app_list`         | Comma-separated app repos (e.g., app-acquisitions,app-bulk-edit)     | Conditional* | string  | -       |
| `workflow_name`    | Workflow filename to toggle (e.g., update-scheduler.yml)             | Yes          | string  | -       |
| `action`           | Action to perform: `enable` or `disable`                             | Yes          | choice  | -       |
| `dry_run`          | Preview changes without applying them                                | No           | boolean | `false` |

\* `platform_branch` is required when `source_type=platform-descriptor`
\* `app_list` is required when `source_type=explicit-list`

### Outputs

This workflow provides results through GitHub Step Summary with detailed statistics and per-repository status.

### Secrets

Inherits secrets from calling environment. No additional secrets required beyond default `GITHUB_TOKEN`.

### Permissions

| Permission  | Level  | Purpose                                    |
|-------------|--------|--------------------------------------------|
| `contents`  | read   | Read platform descriptor from platform-lsp |
| `actions`   | write  | Enable/disable workflows in app repos      |

## 🔄 Workflow Execution Flow

### 1. Validation & Approval

- **Team Authorization**: Validates user is a Kitfox team member via `approve-run.yml`
- **Environment Approval**: Falls back to manual approval if not team member
- **Security Gate**: Ensures only authorized users can modify workflows

### 2. Input Validation

- **Mode Check**: Validates that required inputs are provided based on `source_type`
- **Platform Mode**: Requires `platform_branch` when using platform-descriptor
- **Explicit Mode**: Requires `app_list` when using explicit-list
- **Early Failure**: Exits immediately with clear error if validation fails

### 3. Application List Building

**Platform Descriptor Mode:**
- **Descriptor Fetch**: Uses `fetch-platform-descriptor` action to get descriptor from specified branch
- **App Extraction**: Parses `applications.required` and `applications.optional` arrays
- **Filtering**: Selects only repositories starting with `app-`
- **Deduplication**: Sorts and removes duplicates from combined list

**Explicit List Mode:**
- **Parse Input**: Splits comma-separated list into array
- **Trim Whitespace**: Cleans up spacing from user input
- **Deduplication**: Sorts and removes duplicates
- **Validation**: Ensures at least one valid repository provided

**Output**: JSON array of application names and count for matrix processing

### 4. Parallel Workflow Toggling (Matrix)

- **Matrix Strategy**: Processes each application concurrently
- **Max Parallel**: Limited to 5 concurrent jobs (GitHub API rate limiting consideration)
- **Fail-Fast Disabled**: Continues processing remaining apps even if some fail
- **GitHub CLI**: Uses `gh workflow enable/disable` with `-R folio-org/{app}` flag
- **Dry Run Support**: Lists workflows without making changes when enabled
- **Result Capture**: Each job writes status to JSON file

### 5. Result Collection via Artifacts

- **Artifact Upload**: Each matrix job uploads result JSON as individual artifact
- **Artifact Pattern**: Named `result-{app-name}` for easy identification
- **Status Tracking**: Records one of: `success`, `not_found`, `already_set`, or `error`
- **Message Capture**: Stores detailed message for each outcome
- **Retention**: Results kept for 1 day (sufficient for summary generation)

### 6. Summary Generation & Reporting

- **Artifact Download**: Collects all result artifacts using pattern matching
- **Result Aggregation**: Parses each JSON file and counts by status
- **Rich Summary**: Generates markdown table with status icons:
  - ✅ `success`: Workflow successfully toggled
  - ⚠️ `not_found`: Workflow not found in repository
  - ℹ️ `already_set`: Workflow already in desired state
  - ❌ `error`: Operation failed with error
- **Statistics Block**: Shows total processed, successful, already set, not found, and errors
- **GitHub Step Summary**: Displays comprehensive report in workflow UI

## 🏗️ Architecture Patterns

### Dual-Mode Operation

The workflow uses a choice-based input pattern to cleanly separate two distinct use cases:

**Platform-Descriptor Mode**: Centralized, descriptor-driven approach
```yaml
source_type: platform-descriptor
platform_branch: snapshot
```
- Automatically discovers all apps from platform descriptor
- Ensures consistency with platform definition
- Ideal for platform-wide operations

**Explicit-List Mode**: Targeted, user-controlled approach
```yaml
source_type: explicit-list
app_list: app-acquisitions,app-bulk-edit,app-consortia
```
- User provides exact list of repositories
- Allows selective operations on subset
- Ideal for specific use cases or testing

### Artifact-Based Result Collection

Unlike typical matrix outputs (which are unreliable), this workflow uses artifacts:

1. Each matrix job creates a JSON result file
2. Uploads as uniquely named artifact (`result-{app}`)
3. Summary job downloads all artifacts using pattern
4. Aggregates results into comprehensive report

This pattern ensures reliable result collection even with large matrices.

### Error Handling Strategy

- **Workflow Not Found**: Logged as warning, not failure (may be expected)
- **Already Set**: Logged as informational, considered success
- **Permission Errors**: Logged as error, captured in summary
- **Fail-Fast Disabled**: Ensures all repos processed despite individual failures

## 📚 Use Cases

### 1. Emergency Workflow Disabling

**Scenario**: Scheduled update workflow has a critical bug affecting all apps

```yaml
source_type: platform-descriptor
platform_branch: snapshot
workflow_name: update-scheduler.yml
action: disable
dry_run: false
```

**Result**: Immediately disables problematic workflow across all snapshot applications

### 2. Selective Feature Enablement

**Scenario**: New workflow rolled out to specific apps for testing

```yaml
source_type: explicit-list
app_list: app-acquisitions,app-bulk-edit
workflow_name: new-validation.yml
action: enable
dry_run: false
```

**Result**: Enables new workflow only in specified test applications

### 3. Release Branch Coordination

**Scenario**: Disable snapshot workflows for apps moving to release

```yaml
source_type: platform-descriptor
platform_branch: R1-2025
workflow_name: update-scheduler.yml
action: disable
dry_run: false
```

**Result**: Disables snapshot updates for all apps in release branch

### 4. Safe Testing with Dry Run

**Scenario**: Preview impact before making changes

```yaml
source_type: platform-descriptor
platform_branch: snapshot
workflow_name: update-scheduler.yml
action: disable
dry_run: true
```

**Result**: Shows which repos have the workflow without making changes

### 5. Maintenance Window

**Scenario**: Disable all auto-updates during platform maintenance

```yaml
source_type: platform-descriptor
platform_branch: snapshot
workflow_name: update-scheduler.yml
action: disable
dry_run: false
```

After maintenance:
```yaml
source_type: platform-descriptor
platform_branch: snapshot
workflow_name: update-scheduler.yml
action: enable
dry_run: false
```

## ⚠️ Important Considerations

### GitHub Token Permissions

The workflow requires `actions: write` permission to toggle workflows in other repositories. The `GITHUB_TOKEN` must have appropriate organization-level permissions.

### Workflow Identification

Workflows are identified by filename (e.g., `update-scheduler.yml`), not by workflow name. Ensure you use the exact filename as it appears in the `.github/workflows/` directory.

### Rate Limiting

The workflow is limited to `max-parallel: 5` to avoid GitHub API rate limits when processing many repositories. For large application sets, expect longer execution times.

### Dry Run Testing

Always test with `dry_run: true` first, especially when using platform-descriptor mode, to verify the correct set of applications will be affected.

### Workflow State Persistence

Disabled workflows remain disabled until explicitly re-enabled. They will not automatically re-enable on new commits or workflow file updates.

## 🔍 Troubleshooting

### "Workflow not found" warnings

**Cause**: Target workflow doesn't exist in repository
**Resolution**: Verify workflow filename is correct and exists in app repository

### "Already set" messages

**Cause**: Workflow already in desired state
**Resolution**: This is informational, not an error. No action needed.

### Permission errors

**Cause**: GitHub token lacks `actions: write` permission
**Resolution**: Check token scopes and repository permissions

### Input validation failure

**Cause**: Missing required input for selected `source_type`
**Resolution**: Provide `platform_branch` for platform-descriptor or `app_list` for explicit-list

## 📊 Monitoring & Observability

### Execution Metrics

- **Application Count**: Total repositories processed
- **Success Rate**: Percentage of successful toggles
- **Not Found Rate**: Workflows that don't exist in repos
- **Error Rate**: Failed operations requiring investigation

### Per-Repository Status

Each repository's result includes:
- Repository name
- Status (success/not_found/already_set/error)
- Detailed message explaining outcome

### Dry Run Mode

Dry run executions show:
- Which repositories would be affected
- Whether workflow exists in each repo
- No actual state changes applied

This enables safe pre-validation of bulk operations.