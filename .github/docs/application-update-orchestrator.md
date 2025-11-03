# Application Update Orchestrator

**Workflow**: `application-update-orchestrator.yml`
**Purpose**: Orchestrates application updates across all FOLIO applications in a platform branch
**Type**: Workflow dispatch

## 🎯 Overview

This workflow orchestrates automated updates of all application dependencies within a platform branch. It reads the platform descriptor to identify all applications, fetches their update configurations, and triggers updates in parallel using a dynamically built matrix.

The workflow replaces the previous separate snapshot-update-orchestrator and release-update-orchestrator workflows with a single, configuration-driven solution that works identically for all branch types.

## 📋 Workflow Interface

### Inputs

| Input              | Description                                                             | Required | Type    | Default |
|--------------------|-------------------------------------------------------------------------|----------|---------|---------|
| `platform_branch`  | Platform branch to get application list from (e.g., snapshot, R1-2025)  | Yes      | string  | -       |
| `dry_run`          | Perform dry run without making changes                                  | No       | boolean | `false` |

### Triggers

**Manual**: `workflow_dispatch` only
- Provides platform_branch input for flexibility
- Supports dry-run mode for testing

## 🔄 Workflow Execution Flow

### 1. Authorization Check
**Job**: `approve-run`

Validates that the workflow initiator is a member of the authorized team:

**Process**:
- Uses reusable `approve-run.yml` workflow
- Checks team membership (kitfox team)
- Requires manual approval via "Eureka CI" environment if not authorized
- Blocks execution if approval is denied

### 2. Extract Application List
**Job**: `get-applications`

Fetches platform descriptor and extracts application names:

**Process**:
- Downloads platform-descriptor.json from specified branch
- Parses required and optional applications
- Outputs JSON array of application names
- Used to build matrix for configuration fetching

**Output Example**:
```json
["app-acquisitions", "app-agreements", "app-bulk-edit", ...]
```

### 3. Get Application Configurations
**Job**: `get-app-configurations`

Fetches update configuration for each application in parallel:

**Matrix Strategy**:
```yaml
strategy:
  matrix:
    application: ${{ fromJson(needs.get-applications.outputs.applications) }}
  fail-fast: false
```

**Process**:
- Uses `get-update-config` action for each application
- Fetches `.github/update-config.yml` from application repository
- Validates branch existence
- Filters to enabled branches only
- Stores configuration as job output

### 4. Build Update Matrix
**Job**: `build-matrix`

Combines all application configurations into a single matrix:

**Process**:
- Collects all `branch_config` outputs from previous job
- Uses jq to merge into unified matrix
- Each entry contains:
  - `application`: Application name
  - `branch`: Branch to update
  - `update_branch`: Update branch name (for PRs)
  - `need_pr`: Whether to create PR
  - `pre_release`: Module version filter mode
  - `descriptor_build_offset`: Version offset
  - `rely_on_FAR`: FAR dependency flag
  - `pr_reviewers`: Reviewers list
  - `pr_labels`: Labels list

**Matrix Example**:
```json
[
  {
    "application": "app-acquisitions",
    "branch": "snapshot",
    "update_branch": null,
    "need_pr": false,
    "pre_release": "only",
    "descriptor_build_offset": "100100000000000",
    "rely_on_FAR": false,
    "pr_reviewers": "",
    "pr_labels": ""
  },
  {
    "application": "app-agreements",
    "branch": "R1-2025",
    "update_branch": "version-update/R1-2025",
    "need_pr": true,
    "pre_release": "false",
    "descriptor_build_offset": "",
    "rely_on_FAR": false,
    "pr_reviewers": "folio-org/kitfox",
    "pr_labels": "version-update,automated"
  }
]
```

### 5. Update Applications
**Job**: `update-applications`

Executes updates for all applications in parallel:

**Matrix Strategy**:
```yaml
strategy:
  matrix:
    include: ${{ fromJson(needs.build-matrix.outputs.matrix_includes) }}
  fail-fast: false
  max-parallel: 10
```

**Process**:
- Calls `application-update-flow.yml` for each matrix entry
- Uses GitHub App for cross-repository operations
- Passes all configuration from matrix
- Runs up to 10 updates in parallel
- Continues even if some updates fail

## 🎯 Configuration-Driven Behavior

All application-specific configuration comes from each application's `update-config.yml` file:

### Application Configuration Format

```yaml
update_config:
  enabled: true
  labels:
    - version-update
    - automated
  pr_reviewers:
    - folio-org/kitfox
  update_branch_format: "version-update/{0}"

branches:
  - snapshot:
      enabled: true
      need_pr: false
      pre_release: "only"
      descriptor_build_offset: "100100000000000"
      rely_on_FAR: false
  - R1-2025:
      enabled: true
      need_pr: true
      pre_release: "false"
      descriptor_build_offset: ""
      rely_on_FAR: false
```

### Pre-Release Modes

- **`"only"`**: Updates only snapshot/pre-release versions (for snapshot branch)
- **`"false"`**: Updates only stable release versions (for release branches)
- **`"true"`**: Updates both release and pre-release versions (flexible mode)

## 📊 Usage Examples

### Snapshot Branch Update

```bash
# Via GitHub UI:
# 1. Go to Actions → Application Update Orchestrator
# 2. Click "Run workflow"
# 3. Set platform_branch: snapshot
# 4. dry_run: false
# 5. Click "Run workflow"
```

**Result**:
- Fetches all applications from snapshot platform descriptor
- Updates each application's snapshot branch
- Commits directly (no PRs for snapshot)
- Uses snapshot-only module versions

### Release Branch Update

```bash
# Via GitHub UI:
# 1. Go to Actions → Application Update Orchestrator
# 2. Click "Run workflow"
# 3. Set platform_branch: R1-2025
# 4. dry_run: false
# 5. Click "Run workflow"
```

**Result**:
- Fetches all applications from R1-2025 platform descriptor
- Updates each application's R1-2025 branch
- Creates/updates PRs for review
- Uses release-only module versions

### Dry Run Testing

```bash
# Via GitHub UI:
# Set dry_run: true
```

**Result**:
- Performs all checks and updates
- Does NOT commit changes
- Does NOT create/update PRs
- Useful for testing configuration changes

## 🔍 Features

### Dynamic Matrix Building
- **Automatic discovery**: Reads applications from platform descriptor
- **Configuration merging**: Combines all app configs into one matrix
- **Filtered execution**: Only runs for enabled branches

### Parallel Execution
- **Max parallelism**: Up to 10 concurrent updates
- **fail-fast disabled**: Continues even if some apps fail
- **Resource efficient**: Managed concurrency prevents overload

### Cross-Repository Operations
- **GitHub App auth**: Enhanced permissions for multi-repo operations
- **Secure credentials**: App credentials managed via secrets
- **Audit trail**: All operations tracked with app identity

### Authorization Control
- **Team validation**: Only kitfox team members authorized
- **Manual approval**: Environment protection for unauthorized users
- **Audit logging**: All approvals logged in GitHub

## 🛡️ Error Handling

### Application Not Found

**Scenario**: Application listed in platform descriptor doesn't exist

**Behavior**: Configuration fetch fails for that application, matrix excludes it

**Impact**: Other applications continue to update

### Configuration Missing

**Scenario**: Application doesn't have `update-config.yml`

**Behavior**: Default configuration used, update may be skipped if no enabled branches

**Recovery**: Add configuration file to application repository

### Branch Disabled

**Scenario**: Branch exists but is disabled in configuration

**Behavior**: Branch excluded from matrix, no update attempted

**Logging**: Warning logged during configuration parsing

### Update Failure

**Scenario**: Individual application update fails

**Behavior**: Other applications continue (fail-fast: false)

**Notification**: Failure details in workflow summary

## 📈 Performance Considerations

### Optimization Features

- **Parallel config fetch**: All application configurations fetched simultaneously
- **Efficient matrix**: Single combined matrix vs. separate workflow runs
- **Managed concurrency**: max-parallel prevents resource exhaustion
- **Conditional execution**: Skips unnecessary steps based on configuration

### Resource Management

- **Job distribution**: Spreads load across GitHub runners
- **Rate limiting**: max-parallel respects GitHub API limits
- **Memory efficiency**: Minimal state retention between jobs
- **Cost optimization**: Only runs necessary operations

## 🧪 Testing Strategy

### Pre-Deployment Testing

1. **Dry run**: Test with `dry_run: true`
2. **Small branch**: Test with branch containing few applications
3. **Review logs**: Check matrix building and configuration parsing
4. **Verify no side effects**: Confirm no commits or PRs created

### Validation Checklist

- [ ] Platform descriptor exists for target branch
- [ ] Applications have update-config.yml files
- [ ] Branches specified in configs exist
- [ ] GitHub App credentials configured
- [ ] Slack notification channels configured (optional)
- [ ] Team membership configured correctly

## 📚 Related Documentation

- **[Application Update Flow](../../kitfox-github/.github/docs/application-update-flow.md)**: Core update implementation
- **[Application Update](../../kitfox-github/.github/docs/application-update.md)**: Update orchestrator
- **[Get Update Config](../../kitfox-github/.github/actions/get-update-config/README.md)**: Configuration parsing
- **[Approve Run](approve-run.md)**: Authorization workflow

## 🔍 Troubleshooting

### No Applications Updated

```
Issue: Matrix is empty, no updates run
```

**Possible Causes**:
- Platform descriptor not found for branch
- No applications have enabled branches in their configs
- All application branches are disabled

**Solutions**:
- Verify platform-descriptor.json exists in platform-lsp/{branch}
- Check application update-config.yml files for enabled: true
- Review workflow logs for configuration warnings

### Authorization Failed

```
Issue: Workflow requires approval but user not in team
```

**Solution**: Wait for manual approval from kitfox team member or request team membership

### Partial Updates

```
Issue: Some applications updated, others failed
```

**Behavior**: Expected - fail-fast is disabled to allow partial success

**Action**: Review individual application update logs for failure details

### Configuration Parse Errors

```
Issue: Application excluded from matrix due to config error
```

**Solution**: Validate update-config.yml syntax in affected application repository

---

**Last Updated**: November 2025
**Workflow Version**: 2.0 (Unified)
**Compatibility**: All platform branches (snapshot, R1-2025, R2-2025, etc.)