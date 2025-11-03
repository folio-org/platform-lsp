# Approve Run Workflow

**Workflow**: `approve-run.yml`
**Purpose**: Team-based authorization with manual approval fallback
**Type**: Reusable workflow (`workflow_call`)

## 🎯 Overview

This workflow provides a reusable authorization pattern for critical operations. It validates team membership and requires manual approval for users not in the specified team. The workflow is designed to be called by orchestrator workflows that require access control.

## 📋 Workflow Interface

### Inputs

| Input          | Description                                  | Required | Type   |
|----------------|----------------------------------------------|----------|--------|
| `environment`  | Environment to require manual approval for   | Yes      | string |
| `team`         | GitHub team to validate membership           | Yes      | string |
| `organization` | Organization name                            | Yes      | string |

### Outputs

| Output       | Description                     |
|--------------|---------------------------------|
| `authorized` | Whether the actor is authorized |

### Permissions

No specific permissions required - uses GitHub App token for API access

### Secrets

| Secret                 | Description                 | Required |
|------------------------|-----------------------------|----------|
| `EUREKA_CI_APP_KEY`    | GitHub App private key      | Yes      |

### Variables

| Variable           | Description        | Required |
|--------------------|--------------------|----------|
| `EUREKA_CI_APP_ID` | GitHub App ID      | Yes      |

## 🔄 Workflow Execution Flow

### 1. Validate Actor
**Job**: `validate-actor`

Checks if the workflow initiator is a member of the specified team.

**Process**:
- Generates GitHub App token for API access
- Uses `validate-team-membership` action to check team membership
- Outputs authorization status

### 2. Manual Approval (Conditional)
**Job**: `approve-run`

**Execution Condition**: Only runs if actor is NOT authorized

**Process**:
- Requires manual approval via GitHub Environment protection rules
- Waits for approval from authorized reviewer
- Logs approver information

## 📊 Usage Examples

### Basic Usage

```yaml
jobs:
  authorize:
    uses: folio-org/platform-lsp/.github/workflows/approve-run.yml@master
    with:
      environment: 'Eureka CI'
      team: 'kitfox'
      organization: 'folio-org'
    secrets: inherit

  critical-operation:
    needs: authorize
    if: always() && (needs.authorize.outputs.authorized == 'true' || needs.authorize.result == 'success')
    runs-on: ubuntu-latest
    steps:
      - name: Perform operation
        run: echo "Authorized operation"
```

### In Release Preparation

```yaml
jobs:
  validate-actor:
    uses: folio-org/platform-lsp/.github/workflows/approve-run.yml@master
    with:
      environment: 'Eureka CI'
      team: 'kitfox'
      organization: 'folio-org'
    secrets: inherit

  prepare-release:
    needs: validate-actor
    if: always() && (needs.validate-actor.outputs.authorized == 'true' || needs.validate-actor.result == 'success')
    runs-on: ubuntu-latest
    steps:
      - name: Prepare release
        run: echo "Preparing release"
```

## 🔍 Features

### Team-Based Authorization
- **Direct Access**: Team members proceed immediately
- **Validation**: Real-time GitHub API team membership check
- **Audit Trail**: All authorization decisions logged

### Environment Protection
- **Manual Approval**: Non-team members require approval
- **Reviewers**: Environment protection rules specify approvers
- **Timeout**: Configurable timeout for approval requests

### Flexible Integration
- **Reusable Pattern**: Can be called from any workflow
- **Output-Based Logic**: Downstream jobs use authorization output
- **Non-Blocking**: Approval process doesn't block other workflows

## 🛡️ Error Handling

### Authorization Failures

**Team Member Not Found**:
```
Output: authorized=false
Behavior: Proceeds to manual approval
Recovery: Wait for approval or check team membership
```

**API Errors**:
```
Behavior: Workflow fails with error
Recovery: Check GitHub App configuration and permissions
```

### Approval Timeout

```
Behavior: Workflow times out per environment settings
Recovery: Re-trigger workflow or approve manually
```

## 📈 Performance Considerations

### Optimization Features

- **Early Exit**: Team members skip approval step
- **API Efficiency**: Single team membership check
- **Minimal Overhead**: Quick validation for authorized users

### Resource Management

- **Token Scoping**: GitHub App token scoped to organization
- **Lightweight Jobs**: Simple validation logic
- **No Artifacts**: No artifact creation or storage

## 🔗 Integration Points

### GitHub App Configuration

The workflow requires a GitHub App with:
- **Read access**: Organization members and teams
- **Token generation**: Scoped to organization

### Environment Configuration

Environments must be configured with:
- **Protection Rules**: Required reviewers
- **Timeout**: Approval timeout period
- **Deployment Branches**: Branch restrictions if needed

### Calling Workflows

Workflows using this pattern should:
```yaml
needs: authorize
if: always() && (needs.authorize.outputs.authorized == 'true' || needs.authorize.result == 'success')
```

## 📚 Related Documentation

- **[validate-team-membership Action](../../kitfox-github/.github/actions/validate-team-membership/README.md)**: Team membership validation
- **[Release Preparation Orchestrator](release-preparation-orchestrator.yml)**: Usage example
- **[GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)**: Environment protection rules

---

**Last Updated**: November 2025
**Workflow Version**: 1.0
**Compatibility**: All platform orchestrator workflows