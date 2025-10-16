# Release Update Orchestrator

**Workflow**: `release-update-orchestrator.yml`
**Purpose**: Orchestrates module updates across all application release branches in parallel
**Type**: Platform-level orchestrator workflow

## 🎯 Overview

This workflow serves as the central orchestrator for updating all FOLIO application release branches with the latest module versions. It discovers applications from the platform descriptor, reads per-application release configurations, triggers parallel updates across configured release branches, aggregates results, and provides comprehensive reporting. It's the core automation engine for keeping release branches synchronized with the latest compatible module versions.

## 📋 Workflow Interface

### Inputs

| Input             | Description                                          | Required | Type    | Default |
|-------------------|------------------------------------------------------|----------|---------|---------|
| `platform_branch` | Platform branch to get application list from        | Yes      | string  | -       |
| `dry_run`         | Perform dry run without creating PRs                 | No       | boolean | `false` |

### Outputs

This workflow provides results through GitHub Step Summary and Slack notifications rather than workflow outputs.

### Secrets

| Secret                      | Description                             | Required |
|-----------------------------|-----------------------------------------|----------|
| `EUREKA_CI_APP_KEY`         | GitHub App private key                  | Yes      |
| `EUREKA_CI_SLACK_BOT_TOKEN` | Slack bot token for notifications       | Yes      |

### Variables

| Variable                      | Description                           | Required |
|-------------------------------|---------------------------------------|----------|
| `EUREKA_CI_APP_ID`            | GitHub App ID for cross-repo access   | Yes      |
| `GENERAL_SLACK_NOTIF_CHANNEL` | Slack channel for notifications       | Yes      |

## 🔄 Workflow Execution Flow

### 1. Authorization & Validation
- **Actor Validation**: Checks if triggering user is a Kitfox team member
- **App Token Generation**: Creates GitHub App token for cross-repo access
- **Manual Approval**: Falls back to environment approval if not Kitfox member
- **Security Gate**: Ensures only authorized users can trigger platform-wide updates

### 2. Application Discovery
- **Platform Checkout**: Fetches specified branch from platform-lsp
- **Descriptor Parsing**: Extracts applications from `platform-descriptor.json`
- **Application List**: Generates JSON array of all app-* repositories
- **Count Validation**: Verifies expected number of applications found

### 3. Configuration Collection (Matrix)
- **Matrix Strategy**: Reads configurations from all applications concurrently
- **Fail-Fast Disabled**: Continues even if individual config reads fail
- **Max Parallel**: Limited to 10 concurrent jobs (GitHub resource optimization)
- **Config Action**: Each app's `.github/release-config.yml` read via `get-release-config` action
- **Artifact Upload**: Each configuration stored as artifact for aggregation

### 4. Matrix Building
- **Artifact Download**: Collects all application configurations
- **Configuration Aggregation**: Combines all configs into single JSON structure
- **Matrix Construction**: Builds dynamic matrix of app+branch combinations
- **Enabled Filtering**: Only includes applications with `enabled: true` and configured branches
- **Update Branch Mapping**: Maps each release branch to its corresponding update branch

### 5. Parallel Application Updates (Matrix)
- **Dynamic Matrix**: Processes all app+branch combinations concurrently
- **Fail-Fast Disabled**: Continues even if individual apps fail
- **Max Parallel**: Limited to 10 concurrent jobs
- **Individual Triggers**: Calls `release-update-flow.yml` for each combination
- **GitHub App Auth**: Uses app token for repository permissions
- **Per-App Config**: Passes reviewers, labels, and branch mapping

### 6. Result Collection & Aggregation
- **Output Processing**: Extracts matrix outputs from all update jobs
- **Success/Failure Counting**: Aggregates update statistics
- **Updated Applications**: Lists apps with new module versions
- **PR Tracking**: Counts created pull requests with links
- **Failed Applications**: Captures failure reasons for troubleshooting
- **Comprehensive Metrics**: Generates platform-wide update summary

### 7. Notification & Reporting
- **Slack Notification**: Sends results to configured channel
- **GitHub Step Summary**: Provides rich markdown summary in UI
- **Success Reporting**: Lists all updated applications with PR links
- **Failure Details**: Includes specific error messages for failed apps
- **Dry Run Indication**: Clear messaging when in test mode

## 🏗️ Architecture Patterns

### Per-Application Configuration

Unlike snapshot updates, release updates use decentralized configuration:

```yaml
# .github/release-config.yml in each application repository
enabled: true
release_branches:
  - R1-2025
  - R2-2024
  - R3-2024
update_branches:
  R1-2025: snapshot
  R2-2024: R1-2025
  R3-2024: R2-2024
pr_reviewers: user1,team:kitfox
pr_labels: release-update,automated
```

### Dynamic Matrix Construction

The orchestrator builds a dynamic matrix by combining applications with their configured branches:

```yaml
strategy:
  matrix:
    include: ${{ fromJson(needs.build-matrix.outputs.matrix_includes) }}
  fail-fast: false
  max-parallel: 10

# Matrix includes format:
# [
#   {
#     "application": "app-acquisitions",
#     "release_branch": "R1-2025",
#     "update_branch": "snapshot",
#     "pr_reviewers": "user1,team:kitfox",
#     "pr_labels": "release-update,automated"
#   },
#   ...
# ]
```

### Matrix Building Logic

```bash
# Build matrix includes with app + branch combinations
matrix_includes=$(echo "$all_configs" | jq -c '
  [
    .[]
    | select(.enabled == true and .branch_count > 0)
    | .update_branches_map as $update_map
    | .pr_reviewers as $reviewers
    | .pr_labels as $labels
    | .release_branches[]
    | {
        application: .application,
        release_branch: .,
        update_branch: $update_map[.],
        pr_reviewers: $reviewers,
        pr_labels: $labels
      }
  ]
' <<< "$all_configs")
```

### Result Aggregation Pattern

```bash
# Process matrix outputs to aggregate results
echo "$MATRIX_INCLUDES" | jq -c '.[]' | while IFS= read -r entry; do
  app=$(echo "$entry" | jq -r '.application')
  branch=$(echo "$entry" | jq -r '.release_branch')
  key="${app}_${branch}"

  workflow_status=$(echo "$MATRIX_OUTPUTS" | jq -r --arg key "$key" '.[$key].workflow_status // "unknown"')
  updated=$(echo "$MATRIX_OUTPUTS" | jq -r --arg key "$key" '.[$key].updated // "false"')

  if [[ "$workflow_status" == "success" ]]; then
    ((success_count++))
    if [[ "$updated" == "true" ]]; then
      ((updated_count++))
    fi
  else
    ((failure_count++))
  fi
done
```

## 📊 Usage Examples

### Manual Trigger - Release Branch Update

```yaml
# GitHub UI workflow dispatch
inputs:
  platform_branch: 'R1-2025'
  dry_run: false
```

This will:
1. Read applications from platform descriptor on `R1-2025` branch
2. For each application, read its `.github/release-config.yml`
3. Update all configured release branches with compatible modules
4. Create pull requests for applications with updates
5. Send notifications with aggregated results

### Dry Run Testing

```yaml
# Test updates without creating PRs
inputs:
  platform_branch: 'R1-2025'
  dry_run: true
```

Dry run mode:
- ✅ Checks for module updates across all release branches
- ✅ Validates compatibility and versions
- ❌ Does not create pull requests
- ❌ Does not send notifications
- ✅ Full reporting of what would change

### Multi-Release Branch Update

An application can be configured to track multiple release branches:

```yaml
# app-acquisitions/.github/release-config.yml
enabled: true
release_branches:
  - R1-2025    # Current release
  - R2-2024    # Previous release
  - R3-2024    # Maintenance release
update_branches:
  R1-2025: snapshot           # Get latest from snapshot
  R2-2024: R1-2025            # Get versions from R1-2025
  R3-2024: R2-2024            # Get versions from R2-2024
```

This creates a cascading update pattern where older releases receive compatible versions from newer releases.

## 🛡️ Security & Authorization

### Team-Based Access Control

- **Primary**: Kitfox team members have direct access
- **Fallback**: Manual approval through Eureka CI environment
- **Audit Trail**: All triggers logged with actor information
- **Token Scoping**: GitHub App token limited to necessary permissions

### Environment Protection

```yaml
environment: Eureka CI
# Requires manual approval from authorized approvers
```

### Concurrency Control

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ inputs.platform_branch }}
  cancel-in-progress: false
```

Prevents multiple simultaneous runs for the same platform branch, ensuring update consistency.

## 📈 Performance Optimization

### Parallel Execution

- **Configuration Reading**: Up to 10 applications read concurrently
- **Application Updates**: Up to 10 app+branch combinations updated simultaneously
- **Independent Failures**: One app failure doesn't block others
- **Resource Management**: Balanced to avoid GitHub rate limits
- **Efficient Aggregation**: Results collected in single pass

### Error Resilience

- **Fail-Safe Design**: Continues processing despite individual failures
- **Comprehensive Logging**: Each application provides detailed logs
- **Configuration Flexibility**: Applications can disable scanning independently
- **Clear Error Reporting**: Specific failure reasons for debugging

## 🔍 Monitoring & Observability

### GitHub Step Summary

```markdown
## 🎯 Platform Release Applications Update Summary

### 📊 Overall Statistics
- **Platform Branch**: `R1-2025`
- **Total Applications in Platform**: 31
- **Enabled for Release Scanning**: 25
- **Successfully Processed**: 24
- **Updated Applications**: 15
- **Pull Requests Created**: 15
- **Failed Applications**: 1

### 📦 Updated Applications
- [app-acquisitions/R1-2025 (3)](PR_URL)
- [app-agreements/R1-2025 (5)](PR_URL)
...

### ❌ Failed Applications: app-lists/R1-2025
**Failure Details:**
```
app-lists/R1-2025: Module validation failed
```
```

### Slack Notification Format

**Success Notification:**
```
🚀 *Platform Release Applications Update SUCCESS*

📊 *Statistics:*
• Platform Branch: R1-2025
• Applications Scanned: app-acquisitions, app-agreements, ...
• Updated: 15
• PRs Created: 15

📦 *Updated Applications:*
<PR_URL|app-acquisitions/R1-2025 (3)>
<PR_URL|app-agreements/R1-2025 (5)>
...

🔗 View Details
```

**Failure Notification:**
```
❌ *Platform Release Applications Update FAILED*

📊 *Statistics:*
• Platform Branch: R1-2025
• Applications Scanned: 25
• Failed: 1
• Successfully Processed: 24

❌ *Failed Applications:*
app-lists/R1-2025: Module validation failed

🔗 View Details
```

## 🧪 Testing Strategy

### Dry Run Mode

When `dry_run: true`:
- ✅ All applications checked for updates
- ✅ Validation performed normally
- ✅ Module compatibility verified
- ❌ No pull requests created
- ❌ No Slack notifications sent
- ✅ Full reporting of what would change
- ✅ Safe for testing workflow changes

### Incremental Testing

1. **Single App Configuration**: Test with one app's release-config.yml
2. **Limited Branches**: Configure only one release branch initially
3. **Subset Testing**: Disable most apps, enable a few for validation
4. **Full Dry Run**: Complete platform test without creating PRs
5. **Production Run**: Execute with all safeguards

## 🚨 Troubleshooting

### Common Issues

**Application Configuration Not Found**:
```
Error: Repository 'app-example' has no .github/release-config.yml
Solution: Ensure app has release-config.yml with proper structure
```

**Release Branch Does Not Exist**:
```
Error: Branch 'R1-2025' not found in app-example
Solution: Verify branch exists or update release-config.yml
```

**Invalid Update Branch Mapping**:
```
Error: Update branch 'snapshot' not found for release branch 'R1-2025'
Solution: Verify update_branches mapping in release-config.yml
```

**GitHub Rate Limiting**:
```
Error: API rate limit exceeded
Solution: Reduce max-parallel or wait for limit reset
```

**Invalid Reviewer Names**:
```
Error: Reviewer 'user123' not found
Solution: Verify reviewers are valid GitHub usernames or team slugs (team:teamname)
```

**Module Registry Unavailable**:
```
Error: Failed to fetch module metadata
Solution: Check module registry accessibility and network connectivity
```

### Recovery Procedures

1. **Partial Failure Recovery**:
   - Identify failed applications from summary
   - Check application-specific workflow logs
   - Fix configuration issues
   - Re-run orchestrator for same platform branch

2. **Configuration Issues**:
   - Review application's `.github/release-config.yml`
   - Verify branch mappings are correct
   - Ensure reviewer names are valid
   - Check branch existence in application repos

3. **Complete Failure**:
   - Check GitHub App credentials
   - Verify platform descriptor integrity
   - Review recent infrastructure changes
   - Check Slack token configuration

## 🔄 Integration Points

### Upstream Dependencies

- **Platform Descriptor**: Defines application scope from specified branch
- **Application Configurations**: Each app's `.github/release-config.yml`
- **Module Registry**: Source of module version information
- **GitHub App**: Provides cross-repo permissions

### Downstream Effects

- **Release Branches**: Multiple branches per app updated with compatible modules
- **Pull Requests**: Created with configured reviewers and labels
- **Team Notifications**: Slack alerts on update results
- **Module Version Tracking**: Release branches stay current with compatible versions

### Related Workflows

- **release-update-flow.yml** (kitfox-github): Individual application release update workflow
- **snapshot-update-orchestrator.yml** (platform-lsp): Similar pattern for snapshot updates
- **release-preparation.yml** (platform-lsp): Creates initial release branches

## 📊 Metrics & KPIs

### Success Metrics

- **Update Rate**: Percentage of configured branches successfully updated
- **PR Creation Rate**: Percentage of updates resulting in PRs
- **Module Currency**: How current are release branch module versions
- **Execution Time**: Total workflow duration
- **Failure Rate**: Percentage of failed updates

### Monitoring Points

- GitHub Actions insights
- Slack notification history
- Pull request creation rate
- Module version drift between releases
- Application configuration coverage

## 🎯 Best Practices

### Configuration Management

- **Enable Gradually**: Start with few apps, expand as confidence grows
- **Update Branch Mapping**: Carefully define cascading update sources
- **Reviewer Assignment**: Use team slugs for better maintenance
- **Label Consistency**: Use consistent labels across all apps

### Timing Considerations

- **After Module Releases**: Run after new module versions published
- **Regular Schedule**: Consider weekly or bi-weekly automation
- **Pre-Release Testing**: Run before release candidate creation
- **Coordinate with Team**: Avoid running during active development periods

### Operational Guidelines

1. **Monitor Slack**: Watch for completion notifications
2. **Review PRs**: Check created PRs for unexpected changes
3. **Investigate Failures**: Address failed applications promptly
4. **Update Configurations**: Keep release-config.yml files current
5. **Document Issues**: Log recurring problems for fixes
6. **Coordinate Updates**: Communicate with teams about pending updates

## 🔧 Configuration Reference

### Application Release Configuration

Each application should have `.github/release-config.yml`:

```yaml
# Enable/disable release scanning for this application
enabled: true

# List of release branches to keep updated
release_branches:
  - R1-2025
  - R2-2024

# Map each release branch to its update source
update_branches:
  R1-2025: snapshot      # Get latest from snapshot branch
  R2-2024: R1-2025       # Get versions from R1-2025 branch

# Comma-separated list of PR reviewers (users or teams)
# Teams should be prefixed with "team:"
pr_reviewers: user1,user2,team:kitfox

# Comma-separated list of labels to apply to PRs
pr_labels: release-update,automated,dependencies
```

### Configuration Patterns

**Active Release Only**:
```yaml
enabled: true
release_branches:
  - R1-2025
update_branches:
  R1-2025: snapshot
```

**Multi-Release Cascade**:
```yaml
enabled: true
release_branches:
  - R1-2025
  - R2-2024
  - R3-2024
update_branches:
  R1-2025: snapshot
  R2-2024: R1-2025
  R3-2024: R2-2024
```

**Temporary Disable**:
```yaml
enabled: false  # Temporarily disable scanning
release_branches:
  - R1-2025
```

## 📚 Related Documentation

### Platform Documentation
- **[Release Flow](release-flow.md)**: Overall release CI/CD architecture
- **[Snapshot Flow](snapshot-flow.md)**: Snapshot update processes
- **[Release Preparation](release-preparation.md)**: Initial release branch creation

### Application Documentation
- **[Release Update Flow](../../kitfox-github/.github/docs/release-update-flow.md)**: Individual application workflow
- **[Release Update](../../kitfox-github/.github/docs/release-update.md)**: Module update process for releases

### Implementation References
- [Release Update Orchestrator Workflow](../workflows/release-update-orchestrator.yml)
- [Kitfox GitHub Infrastructure](https://github.com/folio-org/kitfox-github)
- [get-release-config Action](https://github.com/folio-org/kitfox-github/tree/master/.github/actions/get-release-config)
- [Release Update Flow Workflow](https://github.com/folio-org/kitfox-github/blob/master/.github/workflows/release-update-flow.yml)

---

**Last Updated**: October 2025
**Workflow Version**: 1.0
**Platform Compatibility**: Eureka and later releases
