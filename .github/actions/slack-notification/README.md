# FOLIO Platform Slack Notification Action

A reusable GitHub Action for sending standardized Slack notifications for FOLIO platform operations. This action consolidates notification logic and reduces code duplication across workflows.

## Features

- **Unified notification logic**: Single action handles success, failure, and cancelled states
- **Smart formatting**: Automatically formats colors, emojis, and field layouts based on status
- **Rich context**: Includes release information, archive details, and workflow links
- **Flexible messaging**: Supports custom operation types and additional information
- **Error resilient**: Continues workflow execution even if notification fails

## Usage

### Basic Example

```yaml
- name: Send Slack Notification
  uses: ./.github/actions/slack-notification
  with:
    operation_status: success
    release_tag: R1-2025
    workflow_run_id: ${{ github.run_id }}
    slack_channel: '#releases'
    slack_token: ${{ secrets.SLACK_BOT_TOKEN }}
```

### Complete Example

```yaml
- name: Send Release Notification
  uses: ./.github/actions/slack-notification
  with:
    operation_status: ${{ needs.create-artifact.result }}
    operation_type: 'Platform Release Artifact'
    release_tag: ${{ needs.validate.outputs.release_tag }}
    archive_size: ${{ needs.create-artifact.outputs.archive_size }}
    sha256_checksum: ${{ needs.create-artifact.outputs.sha256_checksum }}
    additional_info: 'Release includes 45 applications and 12 modules'
    workflow_run_id: ${{ github.run_id }}
    slack_channel: ${{ vars.SLACK_NOTIFICATION_CHANNEL }}
    slack_token: ${{ secrets.SLACK_BOT_TOKEN }}
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `operation_status` | Operation result (success, failure, cancelled) | ✅ | - |
| `operation_type` | Type of operation performed | ❌ | `'Platform Release'` |
| `release_tag` | Release tag or version | ✅ | - |
| `archive_size` | Archive size in bytes | ❌ | - |
| `sha256_checksum` | SHA256 checksum of archive | ❌ | - |
| `additional_info` | Additional context information | ❌ | `''` |
| `workflow_run_id` | GitHub workflow run ID | ✅ | - |
| `slack_channel` | Slack channel to send notification to | ✅ | - |
| `slack_token` | Slack bot token | ✅ | - |

## Outputs

| Output | Description |
|--------|-------------|
| `message_sent` | Whether the message was sent successfully (true/false) |

## Message Examples

### Success Message
```
✅ FOLIO Platform Release Artifact SUCCESS
View Workflow Run

Release Tag: R1-2025 (linked to GitHub release)
Archive Size: 45MB
Platform: platform-lsp
Trigger: Manual
SHA256 Checksum: `abc123...def456`
```

### Failure Message
```
❌ FOLIO Platform Release Artifact FAILED
View Workflow Run

Release Tag: R1-2025
Failed Job: create-release-artifact
Platform: platform-lsp
Trigger: Release Created
Action Required: Check workflow logs for detailed error information and retry the release process.
```

### Cancelled Message
```
⚠️ FOLIO Platform Release Artifact CANCELLED
View Workflow Run

Release Tag: R1-2025
Status: Cancelled
Platform: platform-lsp
Trigger: Manual
```

## Status Handling

The action automatically handles different operation statuses:

- **success**: Green color (good), ✅ emoji, includes archive details and checksum
- **failure**: Red color (danger), ❌ emoji, includes error guidance
- **cancelled**: Orange color (warning), ⚠️ emoji, shows cancellation status
- **other**: Default blue color (good), ℹ️ emoji, generic completion message

## Requirements

### Slack Configuration
- Slack bot token with `chat:write` permissions
- Bot must be invited to the target channel
- Channel can be public (`#channel`) or private

### GitHub Permissions
```yaml
permissions:
  contents: read  # To checkout repository and access action
```

## Integration Patterns

### Conditional Notifications
```yaml
- name: Send Success Notification
  if: needs.main-job.result == 'success'
  uses: ./.github/actions/slack-notification
  with:
    operation_status: success
    # ... other inputs

- name: Send Failure Notification
  if: needs.main-job.result == 'failure'
  uses: ./.github/actions/slack-notification
  with:
    operation_status: failure
    additional_info: 'Build failed during validation phase'
    # ... other inputs
```

### Matrix Result Notifications
```yaml
- name: Send Batch Results
  uses: ./.github/actions/slack-notification
  with:
    operation_status: ${{ steps.aggregate.outputs.overall_status }}
    operation_type: 'Batch Application Release'
    additional_info: 'Processed ${{ steps.aggregate.outputs.success_count }} applications successfully'
    # ... other inputs
```

## Error Handling

The action uses `continue-on-error: true` internally, so notification failures won't break your workflow. Check the `message_sent` output to handle notification failures:

```yaml
- name: Send Notification
  id: notify
  uses: ./.github/actions/slack-notification
  with:
    # ... inputs

- name: Handle Notification Failure
  if: steps.notify.outputs.message_sent == 'false'
  run: echo "::warning::Failed to send Slack notification"
```

## Customization

### Custom Operation Types
```yaml
with:
  operation_type: 'Security Scan'
  # or
  operation_type: 'Performance Test'
  # or
  operation_type: 'Integration Deployment'
```

### Dynamic Additional Info
```yaml
with:
  additional_info: ${{ needs.build.result == 'failure' && 'Build failed during compilation' || format('Deployed to {0} environment', inputs.environment) }}
```

## Benefits Over Direct Slack API Usage

1. **Reduced Duplication**: One action replaces multiple similar notification steps
2. **Consistent Formatting**: Standardized message layout and styling
3. **Smart Defaults**: Automatic color/emoji selection based on status
4. **Error Resilience**: Built-in error handling and fallbacks
5. **Maintenance**: Single location for notification logic updates
6. **Reusability**: Can be used across multiple workflows and repositories

## Contributing

This action is part of the FOLIO platform infrastructure. For improvements:

1. Test changes thoroughly with different status types
2. Ensure backward compatibility with existing workflows
3. Update documentation for any new features
4. Follow FOLIO coding standards and security practices

## License

Apache License 2.0 - See the LICENSE file in the repository root.
