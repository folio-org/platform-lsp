# Applications Snapshot Update Orchestrator

**Workflow**: `apps-snapshot-update.yml`  
**Purpose**: Orchestrates snapshot updates across all FOLIO applications in parallel  
**Type**: Platform-level orchestrator workflow

## 🎯 Overview

This workflow serves as the central orchestrator for updating all FOLIO applications with the latest module versions. It extracts applications from the platform descriptor, triggers parallel updates across 30+ repositories, aggregates results, and provides comprehensive reporting. It's the core automation engine for FOLIO's continuous integration at the platform level.

## 📋 Workflow Interface

### Inputs

| Input                    | Description                                          | Required | Type    | Default             |
|--------------------------|------------------------------------------------------|----------|---------|---------------------|
| `descriptor_build_offset`| Offset to apply to application artifact version      | No       | string  | `'100100000000000'` |
| `rely_on_FAR`            | Whether to rely on FAR for dependency validation     | No       | boolean | `false`             |
| `dry_run`                | Perform dry run without making changes               | No       | boolean | `false`             |

### Outputs

This workflow provides results through artifacts and GitHub Step Summary rather than workflow outputs.

### Secrets

| Secret               | Description                             | Required |
|----------------------|-----------------------------------------|----------|
| `EUREKA_CI_APP_ID`   | GitHub App ID for cross-repo operations | Yes      |
| `EUREKA_CI_APP_KEY`  | GitHub App private key                  | Yes      |
| `SLACK_BOT_TOKEN`    | Slack bot token for notifications       | Yes      |

## 🔄 Workflow Execution Flow

### 1. Authorization & Validation
- **Actor Validation**: Checks if triggering user is a Kitfox team member
- **App Token Generation**: Creates GitHub App token for cross-repo access
- **Manual Approval**: Falls back to environment approval if not Kitfox member
- **Security Gate**: Ensures only authorized users can trigger platform-wide updates

### 2. Application Discovery
- **Platform Checkout**: Fetches snapshot branch of platform-lsp
- **Descriptor Parsing**: Extracts applications from `platform-descriptor.json`
- **Application List**: Generates JSON array of all app-* repositories
- **Count Validation**: Verifies expected number of applications found

### 3. Parallel Application Updates (Matrix)
- **Matrix Strategy**: Processes all applications concurrently
- **Fail-Fast Disabled**: Continues even if individual apps fail
- **Max Parallel**: Limited to 5 concurrent jobs (GitHub resource optimization)
- **Individual Triggers**: Each app's `app-snapshot-update.yml` workflow
- **GitHub App Auth**: Uses app token for repository permissions

### 4. Result Collection & Aggregation
- **Artifact Download**: Collects results from all application workflows
- **Success/Failure Counting**: Aggregates update statistics
- **Updated Applications**: Lists apps with new module versions
- **Failed Applications**: Captures failure reasons for troubleshooting
- **Comprehensive Metrics**: Generates platform-wide update summary

### 5. Notification & Reporting
- **Slack Notification**: Sends results to configured channel
- **GitHub Step Summary**: Provides rich markdown summary in UI
- **Success Reporting**: Lists all updated applications with links
- **Failure Details**: Includes specific error messages for failed apps
- **Dry Run Indication**: Clear messaging when in test mode

## 🏗️ Architecture Patterns

### Matrix Processing Strategy
```yaml
strategy:
  matrix:
    application: ${{ fromJson(needs.get-applications.outputs.applications) }}
  fail-fast: false
  max-parallel: 5
```

### Cross-Repository Orchestration
```yaml
- name: Update Application
  uses: actions/github-script@v7
  with:
    github-token: ${{ steps.app-token.outputs.token }}
    script: |
      await github.rest.actions.createWorkflowDispatch({
        owner: 'folio-org',
        repo: '${{ matrix.application }}',
        workflow_id: 'app-snapshot-update.yml',
        ref: 'master',
        inputs: {
          descriptor_build_offset: '${{ inputs.descriptor_build_offset }}',
          rely_on_FAR: '${{ inputs.rely_on_FAR }}',
          dry_run: '${{ inputs.dry_run }}'
        }
      })
```

### Result Aggregation Pattern
```bash
# Collect results from all applications
for result_file in result-*.json; do
  if jq -e '.updated == "true"' "$result_file" >/dev/null 2>&1; then
    ((updated_count++))
    # Extract application details for reporting
  fi
done
```

## 📊 Usage Examples

### Manual Trigger - Production Update
```yaml
# GitHub UI workflow dispatch
inputs:
  descriptor_build_offset: '100100000000000'
  rely_on_FAR: false
  dry_run: false
```

### Dry Run Testing
```yaml
# Test updates without committing changes
inputs:
  descriptor_build_offset: '100100000000000'
  rely_on_FAR: false
  dry_run: true
```

### FAR Validation Mode
```yaml
# Use FAR for dependency validation
inputs:
  descriptor_build_offset: '100100000000000'
  rely_on_FAR: true
  dry_run: false
```

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

## 📈 Performance Optimization

### Parallel Execution
- **Concurrent Processing**: Up to 5 applications updated simultaneously
- **Independent Failures**: One app failure doesn't block others
- **Resource Management**: Balanced to avoid GitHub rate limits
- **Efficient Aggregation**: Results collected in single pass

### Error Resilience
- **Fail-Safe Design**: Continues processing despite individual failures
- **Comprehensive Logging**: Each application provides detailed logs
- **Retry Capability**: Failed apps can be manually retriggered
- **Clear Error Reporting**: Specific failure reasons for debugging

## 🔍 Monitoring & Observability

### GitHub Step Summary
```markdown
## 🎯 Platform Snapshot Applications Update Summary

### 📊 Overall Statistics
- **Total Applications**: 31
- **Successfully Processed**: 29
- **Updated Applications**: 15
- **Failed Applications**: 2

### ✅ Updated Applications
- [app-acquisitions](https://github.com/folio-org/app-acquisitions/actions/runs/12345)
- [app-agreements](https://github.com/folio-org/app-agreements/actions/runs/12346)
...

### ❌ Failed Applications
**app-lists**: Module validation failed
**app-oa**: Network timeout
```

### Slack Notification Format
```
🚀 *Platform Snapshot Update Complete*

📊 *Statistics:*
• Total: 31 applications
• Success: 29 (93.5%)
• Updated: 15
• Failed: 2

✅ *Updated:* app-acquisitions, app-agreements, ...
❌ *Failed:* app-lists (validation), app-oa (timeout)

🔗 <workflow_url|View Details>
```

## 🧪 Testing Strategy

### Dry Run Mode
When `dry_run: true`:
- ✅ All applications checked for updates
- ✅ Validation performed normally
- ❌ No commits or pushes made
- ✅ Full reporting of what would change
- ✅ Safe for testing workflow changes

### Incremental Testing
1. **Single App Test**: Test with modified platform descriptor
2. **Subset Test**: Include only few apps for validation
3. **Full Dry Run**: Complete platform test without changes
4. **Production Run**: Execute with all safeguards

## 🚨 Troubleshooting

### Common Issues

**Application Not Found**:
```
Error: Repository 'app-example' not found
Solution: Verify app exists in platform-descriptor.json
```

**GitHub Rate Limiting**:
```
Error: API rate limit exceeded
Solution: Reduce max-parallel or wait for limit reset
```

**Workflow Not Found**:
```
Error: Workflow 'app-snapshot-update.yml' not found in app-X
Solution: Ensure all apps have required workflow file
```

**Authentication Failures**:
```
Error: Resource not accessible by integration
Solution: Verify GitHub App installation on repository
```

### Recovery Procedures

1. **Partial Failure Recovery**:
   - Identify failed applications from summary
   - Manually trigger individual app workflows
   - Rerun orchestrator after fixes

2. **Complete Failure**:
   - Check GitHub App credentials
   - Verify platform descriptor integrity
   - Review recent infrastructure changes

## 🔄 Integration Points

### Upstream Dependencies
- **Module Releases**: Triggers when new module versions available
- **Platform Descriptor**: Defines application scope
- **GitHub App**: Provides cross-repo permissions

### Downstream Effects
- **Application Updates**: Each app's snapshot branch updated
- **FAR Registry**: New application versions published
- **Test Environments**: Updated artifacts available
- **Developer Notifications**: Slack alerts on changes

## 📊 Metrics & KPIs

### Success Metrics
- **Update Rate**: Percentage of apps successfully updated
- **Module Currency**: How current are module versions
- **Execution Time**: Total workflow duration
- **Failure Rate**: Percentage of failed updates

### Monitoring Points
- GitHub Actions insights
- Slack notification history
- Application version drift
- Module update frequency

## 🎯 Best Practices

### Timing Considerations
- **Off-Peak Hours**: Run during low-activity periods
- **Regular Schedule**: Consider automation via cron
- **Pre-Release Checks**: Run before release preparations
- **Post-Module Updates**: Trigger after module deployments

### Operational Guidelines
1. **Monitor Slack**: Watch for completion notifications
2. **Review Failures**: Investigate any failed applications
3. **Verify Updates**: Check critical apps manually
4. **Document Issues**: Log recurring problems for fixes

## 📚 Related Documentation

- **[Snapshot Flow](snapshot-flow.md)**: Overall snapshot CI/CD architecture
- **[Release Preparation](release-preparation.md)**: Release branch workflow
- **[Snapshot Update Flow](../../kitfox-github/.github/docs/snapshot-update-flow.md)**: Individual app workflow
- **[Platform Descriptor](../../../README.md)**: Platform configuration

---

**Last Updated**: September 2025  
**Workflow Version**: 2.0  
**Platform Compatibility**: Eureka and later releases
