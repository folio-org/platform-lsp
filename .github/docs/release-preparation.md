# Release Preparation - Coordinated Release Management

**Orchestrated preparation of release branches across the entire FOLIO ecosystem**

The Release Preparation process represents the most complex and critical component of the FOLIO Eureka CI/CD pipeline. It coordinates the creation of release branches, version alignment, and cross-repository synchronization to prepare the entire FOLIO platform for an official release.

## 🎯 Purpose and Scope

Release Preparation orchestrates the transition from continuous development to structured release by:

- **Creating release branches** across 31+ application repositories and the platform
- **Coordinating version alignment** between modules, applications, and platform components
- **Managing distributed workflows** with comprehensive monitoring and reporting
- **Ensuring release readiness** through two-phase validation and execution
- **Providing comprehensive visibility** through dual notification systems

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              RELEASE PREPARATION ARCHITECTURE           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🎯 ORCHESTRATOR (platform-lsp)                         │
│  ├─ Team Authorization (Kitfox Team)                    │
│  ├─ Application Discovery & Merging                     │
│  ├─ Two-Phase Matrix Orchestration                      │
│  ├─ Result Collection & Aggregation                     │
│  ├─ Platform State Preparation                          │
│  └─ Comprehensive Slack Notifications                   │
│                                                         │
│  🚀 DISTRIBUTED EXECUTION                               │
│  ├─ Phase 1: Validation (Check Applications)            │
│  │  ├─ Dry Run Validation Across All Apps               │
│  │  ├─ Branch Verification                              │
│  │  ├─ Version Validation                               │
│  │  └─ Prerequisites Check                              │
│  │                                                      │
│  ├─ Phase 2: Execution (Update Applications)            │
│  │  ├─ Branch Creation                                  │
│  │  ├─ Version Updates                                  │
│  │  ├─ Descriptor Modifications                         │
│  │  └─ Individual App Notifications                     │
│  │                                                      │
│  └─ Phase 3: Platform Integration                       │
│     ├─ Platform Template Updates (^VERSION constraints) │
│     ├─ Platform Branch Creation                         │
│     ├─ Config Management (update-config.yml)            │
│     └─ Platform Release Branch Push                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 📋 Process Documentation Integration

*Based on [Release Preparation Process](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/886178625/Release+preparation)*

The release preparation process combines the official FOLIO release methodology with the implemented distributed workflow system, ensuring both compliance with FOLIO standards and operational efficiency through automation.

## 🚀 Implementation Overview

### Production-Ready Status

The distributed release preparation workflow has undergone comprehensive testing across the entire FOLIO ecosystem with proven capabilities:

- **✅ Success Scenarios**: Complete end-to-end workflow with all 31 applications succeeding
- **✅ Failure Scenarios**: Intentional failure testing with proper error aggregation  
- **✅ Two-Phase Validation**: Check phase followed by execution phase
- **✅ Comprehensive Monitoring**: UUID-based tracking with complete visibility
- **✅ Team Authorization**: Kitfox team validation implemented and verified
- **✅ Dual Notification System**: Platform-level and individual app notifications

### Key Metrics
- **31 Application Repositories**: All updated with reusable workflows
- **Parallel Processing**: Matrix strategy with 5 concurrent executions
- **Fault Isolation**: Individual failures don't block entire release
- **Result Aggregation**: Failed application collection and comprehensive reporting

## 🔧 Technical Implementation

### Manual Trigger (Kitfox Team Only)

**Workflow**: `release-preparation.yml` in platform-lsp repository

**Trigger**: `workflow_dispatch` with manual parameter input

**Required Inputs**:
```yaml
inputs:
  previous_release_branch: "R2-2024"      # Source release branch
  new_release_branch: "R1-2025"          # Target release branch
  new_applications: "app-new1,app-new2"  # Optional new applications (flexible input)
  use_snapshot_fallback: false           # Use snapshot branch if previous not found
  use_snapshot_version: false            # Use snapshot version as base
  dry_run: true                          # Test mode (default)

  # Platform-specific configuration (optional)
  branch_name: "FOLIO Sunflower Release" # Display name for the release branch
  branch_description: "FOLIO LSP..."     # Description for the release branch

  # Update configuration settings (optional)
  need_pr: true                          # Require PR for version updates (default: true)
  prerelease_mode: "false"               # Module version constraints: "false", "true", or "only" (default: "false")
```

### Authorization Architecture

**Security Model**: Kitfox team-controlled initiation with reusable authorization workflow

```yaml
jobs:
  authorize:
    name: Authorize Run
    uses: ./.github/workflows/approve-run.yml
    with:
      environment: 'Eureka CI'
      team: 'kitfox'
      organization: 'folio-org'
    secrets: inherit
```

**Authorization Features**:
- **Team Validation**: Automatic Kitfox team membership check
- **Environment Protection**: Manual approval required for non-team members
- **Reusable Pattern**: Consistent authorization across all orchestrators
- **Audit Trail**: All authorization decisions logged

### Distributed Workflow Architecture

The implementation uses a **two-layer distributed workflow architecture**:

#### Layer 1: Orchestrator (platform-lsp)
- **Authorization**: Team validation and approval management
- **Discovery**: Application list extraction and merging
- **Orchestration**: Matrix coordination calling `release-preparation-flow.yml` directly
- **Aggregation**: Result collection from workflow artifacts
- **Notification**: Platform-level success/failure reporting

#### Layer 2: Reusable Workflows (kitfox-github)
The orchestrator directly calls centralized workflows using `uses:` syntax in matrix jobs:

**Two-Workflow Architecture**:
1. **`release-preparation-flow.yml`** - Core logic workflow
   - Template updates with `^VERSION` placeholders and `preRelease: "false"` flags
   - Version management and branch creation
   - Update-config.yml management with configurable `need_pr` and `prerelease_mode`
   - Result artifact upload for orchestrator collection
   - Called directly by platform orchestrator in matrix jobs

2. **`release-preparation.yml`** - Public wrapper workflow
   - Calls `release-preparation-flow.yml` for core logic
   - Adds integrated notifications (team + general channels)
   - Provides workflow summary
   - Used by applications for individual release preparation

**Benefits**:
- **Pure Functionality**: No authorization logic - just execution
- **Centralized Maintenance**: Single point to change approach when needed
- **Matrix Compatibility**: Flow workflow can be called directly in matrix
- **Artifact-Based Results**: Flow uploads results for orchestrator aggregation
- **Approach Propagation**: Public wrapper ensures consistent pattern across applications

> 📚 **Detailed Documentation**: See [Release Preparation Workflow Guide](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/release-preparation.md) for comprehensive technical documentation of the workflow architecture and patterns.

### Universal Actions Implementation

**Composite Actions** (folio-org/kitfox-github):

> 📋 **Action Documentation**: Each action includes comprehensive usage guides with examples. See [Universal Actions](https://github.com/folio-org/kitfox-github/blob/master/.github/README.md#-universal-actions) for complete documentation.

#### 1. validate-team-membership
```yaml
- uses: folio-org/kitfox-github/.github/actions/validate-team-membership@master
  with:
    username: ${{ github.actor }}
    organization: 'folio-org'
    team: 'kitfox'
```

#### 2. collect-app-version
```yaml
- uses: folio-org/kitfox-github/.github/actions/collect-app-version@master
  with:
    app_name: ${{ matrix.application }}
    branch: ${{ inputs.new_release_branch }}
```

### Reusable Workflows Implementation

**Reusable Workflows** (folio-org/kitfox-github):

#### 1. release-preparation-flow.yml
- **Purpose**: Core release preparation logic
- **Features**: Template updates, version management, branch creation, result artifact upload
- **Integration**: Called directly by platform orchestrator in matrix jobs

#### 2. release-preparation.yml
- **Purpose**: Public wrapper with integrated notifications
- **Features**: Calls flow workflow, sends Slack notifications (team + general), generates workflow summary
- **Integration**: Called by individual application repositories for team-level workflows

## 🔄 Workflow Execution Flow

### Phase 1: Authorization and Discovery

```yaml
1. Team Authorization
   ├─ Kitfox team membership validation
   ├─ Environment-based fallback approval
   └─ Audit trail creation

2. Application Discovery  
   ├─ Extract applications from platform-descriptor.json
   ├─ Merge with new applications (flexible input parsing)
   ├─ Validate application repositories exist
   └─ Generate matrix for parallel processing
```

### Phase 2: Two-Phase Distributed Orchestration

#### Phase 2a: Validation (Check Applications)
```yaml
check-applications:
  name: Check ${{ matrix.application }} Application
  strategy:
    matrix:
      application: ${{ fromJson(needs.initial-check.outputs.applications) }}
    fail-fast: false    # Continue even if some apps fail
    max-parallel: 5     # Optimal resource utilization
  uses: folio-org/kitfox-github/.github/workflows/release-preparation-flow.yml@master
  with:
    app_name: ${{ matrix.application }}
    repo: folio-org/${{ matrix.application }}
    previous_release_branch: ${{ inputs.previous_release_branch }}
    new_release_branch: ${{ inputs.new_release_branch }}
    use_snapshot_fallback: ${{ inputs.use_snapshot_fallback }}
    use_snapshot_version: ${{ inputs.use_snapshot_version }}
    dry_run: true  # Always dry run for validation
  secrets: inherit
```

#### Phase 2b: Execution (Update Applications)
```yaml
update-applications:
  name: Prepare ${{ matrix.application }} Application
  needs: [initial-check, check-applications]
  if: inputs.dry_run != true
  strategy:
    matrix:
      application: ${{ fromJson(needs.initial-check.outputs.applications) }}
    fail-fast: false
    max-parallel: 5
  uses: folio-org/kitfox-github/.github/workflows/release-preparation-flow.yml@master
  with:
    app_name: ${{ matrix.application }}
    repo: folio-org/${{ matrix.application }}
    previous_release_branch: ${{ inputs.previous_release_branch }}
    new_release_branch: ${{ inputs.new_release_branch }}
    use_snapshot_fallback: ${{ inputs.use_snapshot_fallback }}
    use_snapshot_version: ${{ inputs.use_snapshot_version }}
    dry_run: ${{ inputs.dry_run }}  # Actual dry_run value
  secrets: inherit
```

### Phase 3: Result Collection & Aggregation

```yaml
collect-results:
  needs: [initial-check, update-applications]
  if: always() && needs.update-applications.result != 'skipped'

  steps:
    - name: Download All Application Results
      uses: actions/download-artifact@v4
      with:
        pattern: "result-*"
        path: /tmp/all-results
        merge-multiple: true

    - name: Gather Application Results
      id: gather-failures
      run: |
        all=$(jq -s '.' /tmp/all-results/*.json)

        success_count=$(jq '[.[] | select(.status=="success")] | length' <<<"$all")
        failure_count=$(jq '[.[] | select(.status!="success")] | length' <<<"$all")
        failed_apps=$(jq -r '[.[] | select(.status!="success") | .application] | join(", ")' <<<"$all")

        echo "failed_apps=$failed_apps" >> "$GITHUB_OUTPUT"
        echo "success_count=$success_count" >> "$GITHUB_OUTPUT"
        echo "failure_count=$failure_count" >> "$GITHUB_OUTPUT"
```

### Phase 4: Platform Preparation

```yaml
prepare-platform:
  needs: [collect-results]
  if: needs.collect-results.outputs.failure_count == '0'

  steps:
    - name: Update Platform Template
      run: |
        # Update platform-descriptor.template.json with version constraints and preRelease flags
        # Set application versions to ^FULL.VERSION with preRelease: "false" (e.g., ^2.3.1)
        # Set eureka-components to ^VERSION placeholder with preRelease: "false"
        # Set platform version to <new_release_branch>.0
        # Upload as artifact

update-platform-config:
  needs: [initial-check, prepare-platform]
  steps:
    - name: Manage Update Config
      run: |
        # Create/update .github/update-config.yml on default branch
        # Add new release branch to tracked branches with configuration:
        #   - enabled: true (always enabled for new release branches)
        #   - need_pr: <from input parameter> (default: true)
        #   - preRelease: <from input parameter> (default: "false")
        #   - name: <from input parameter> (optional, platform-specific)
        #   - description: <from input parameter> (optional, platform-specific)
        # Use jq to dynamically build branch configuration
        # Use yq for reliable YAML manipulation
        # Upload as artifact with include-hidden-files: true to preserve .github/ structure

commit-platform-changes:
  uses: folio-org/kitfox-github/.github/workflows/commit-and-push-changes.yml@master
  with:
    # Commit template to release branch
    # Delete platform-descriptor.json (regenerated by CI)

commit-platform-config:
  uses: folio-org/kitfox-github/.github/workflows/commit-and-push-changes.yml@master
  with:
    # Commit config to default branch
```

### Phase 5: Comprehensive Notifications

```yaml
slack_notification:
  needs: [collect-results, prepare-platform]
  if: always() && inputs.dry_run == false
  
  steps:
    - name: Send SUCCESS Slack Notification
      if: needs.prepare-platform.result == 'success'
      uses: slackapi/slack-github-action@v2.1.1
      with:
        payload: |
          # Platform-level success notification with metrics
          
    - name: Send FAILED Slack Notification  
      if: needs.prepare-platform.result != 'success'
      uses: slackapi/slack-github-action@v2.1.1
      with:
        payload: |
          # Detailed failure reporting with failed application list
```

## ✋ After the branch is cut: replace the placeholders

The orchestrator leaves every `eureka-components` entry as `^VERSION_<previous>` — a placeholder, not a constraint. Component versions for a new release are not known at preparation time, so a human fills them in.

The branch is added to `update-config.yml` with `enabled: true`, so `release-scan.yml` picks it up on the next hourly tick. Until the placeholders are replaced, `release-update-flow.yml` finds them, warns, and skips the branch:

```
::warning::Descriptor template still holds unresolved placeholders, skipping update:
eureka-components[folio-kong].version='^VERSION_3.9.1'
```

The run stays green — this is a "not yet", not a failure. Nothing is committed and no PR is opened until someone edits `platform-descriptor.template.json` and replaces each `^VERSION_<x>` with a real constraint.

Two things to get right in that edit:

- **The constraint form.** `^X.Y.Z` tracks the minor, `~X.Y.Z` the patch, a plain version pins outright. `latest` is for `snapshot`, not for a release branch.
- **The platform `version`.** The orchestrator writes `<branch>.0`; leave the trailing build segment in place. `calculate-version-increment` needs it, and without it the branch reports no update on every run.

The first successful scan after that creates `platform-descriptor.json` on the branch — the orchestrator deliberately does not, since resolved versions are the update flow's output, not preparation's.

## 🔍 Advanced Features

### Flexible Input Processing

**Multi-Format Support**: Applications can be specified in multiple formats:
```bash
# Comma-separated
"app-one,app-two,app-three"

# Space-separated  
"app-one app-two app-three"

# Newline-separated
"app-one
app-two
app-three"

# Mixed formats
"app-one, app-two
app-three"
```

**Implementation**: Uses robust `jq` parsing with `gsub("[,[:space:]]+"; "\n")` for normalization

### UUID-Based Workflow Tracking

**Problem Solved**: GitHub workflow run IDs are not immediately available after triggering

**Solution**: Generate unique dispatch IDs for reliable workflow tracking
```bash
dispatch_id=$(uuidgen)
gh workflow run release-preparation.yml \
  --repo "folio-org/$APP_NAME" \
  --ref master \
  -f dispatch_id="$dispatch_id"

# Poll for workflow using dispatch_id
run_id=$(gh run list \
  --workflow release-preparation.yml \
  --repo "folio-org/$APP_NAME" \
  --json databaseId,displayTitle \
  --jq "map(select(.displayTitle | contains(\"$dispatch_id\")))[0].databaseId")
```

### Result Aggregation System

**Challenge**: Collecting results from 31+ parallel matrix jobs

**Solution**: Artifact-based result collection with `jq` aggregation
```yaml
# Each matrix job uploads result artifact (from release-preparation-flow.yml)
- name: Upload Result
  uses: actions/upload-artifact@v4
  with:
    name: "result-${{ inputs.app_name }}"
    path: "/tmp/results/${{ inputs.app_name }}.json"

# Aggregation job downloads and processes all results
- name: Download All Results
  uses: actions/download-artifact@v4
  with:
    pattern: "result-*"
    path: /tmp/all-results
    merge-multiple: true

- name: Aggregate Results
  run: |
    all=$(jq -s '.' /tmp/all-results/*.json)
    success_count=$(jq '[.[] | select(.status=="success")] | length' <<<"$all")
    failure_count=$(jq '[.[] | select(.status!="success")] | length' <<<"$all")
    failed_apps=$(jq -r '[.[] | select(.status!="success") | .application] | join(", ")' <<<"$all")
```

## 📊 Monitoring and Observability

### Comprehensive Logging

**GitHub Actions Annotations**:
```bash
echo "::group::Application Discovery"
echo "::notice::Found $count applications to process"
echo "::endgroup::"

echo "::error title=Authorization Failed::User not in Kitfox team"
echo "::warning title=Fallback Used::Using snapshot branch as previous not found"
```

### Real-Time Progress Tracking

**Matrix Job Monitoring**: Each application processed in parallel with individual progress tracking
**UUID Tracking**: Reliable workflow identification across distributed system
**Status Aggregation**: Real-time collection of success/failure counts

### Dual Notification System

**Platform-Level Notifications**: Comprehensive release preparation summary
**Individual App Notifications**: Per-application success/failure reporting
**Slack Integration**: Real-time team notifications with detailed context

## 🚨 Error Handling and Recovery

### Fault Isolation

**Principle**: Individual application failures don't block entire release preparation

**Implementation**:
```yaml
strategy:
  matrix:
    application: ${{ fromJson(needs.initial-check.outputs.applications) }}
  fail-fast: false  # Critical for fault isolation
```

### Comprehensive Error Reporting

**Failed Application Collection**: Automatically identify and report failed applications
**Detailed Failure Context**: Specific error messages and workflow links
**Recovery Guidance**: Clear instructions for addressing failures

### Two-Phase Safety

**Phase 1: Validation**: Dry run across all applications to identify issues early
**Phase 2: Execution**: Real execution only after successful validation
**Safety Gate**: Execution phase only runs if validation phase succeeds

## 📈 Performance and Scalability

### Parallel Processing Optimization

**Concurrent Execution**: 5 parallel matrix jobs for optimal resource utilization
**Processing Time**: ~15-20 minutes for complete ecosystem preparation
**Resource Efficiency**: Balanced GitHub Actions runner usage

### Scalability Features

**Dynamic Matrix**: Automatically adjusts to new applications
**Flexible Input**: Supports adding new applications on-the-fly
**Extensible Architecture**: Easy to add new processing steps or validations

## 🔧 Implementation Status

### Current Capabilities
- ✅ **Team Authorization**: Kitfox team validation with environment fallback
- ✅ **Distributed Orchestration**: 31+ repository coordination  
- ✅ **Two-Phase Processing**: Validation followed by execution
- ✅ **Result Aggregation**: Comprehensive failure and success reporting
- ✅ **Platform Integration**: Complete platform state preparation
- ✅ **Dual Notifications**: Platform and application-level messaging
- ✅ **Fault Isolation**: Individual failures don't block entire process
- ✅ **UUID Tracking**: Reliable distributed workflow monitoring

### Operational Readiness
- ✅ **Production Tested**: Comprehensive testing across entire ecosystem
- ✅ **Performance Validated**: 5x faster than sequential processing
- ✅ **Error Handling**: Robust failure detection and reporting
- ✅ **Team Adoption**: Successfully deployed across all 31 applications

## 🔗 Related Documentation

### Platform Documentation
- [Platform Architecture](../../README.md)
- [Release Preparation Process](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/886178625/Release+preparation)
- [Eureka CI Flow Documentation](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887488514/CI+flow+release)

### Technical Implementation Guides
The release preparation process relies heavily on the shared infrastructure provided by kitfox-github:

- **[Release Preparation Workflow](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/release-preparation.md)** - Individual application release preparation workflow
- **[Release Preparation Flow](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/release-preparation-flow.md)** - Core release preparation logic workflow
- **[Application Update](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/application-update.md)** - Application update orchestrator workflow
- **[Commit and Push Changes](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/commit-and-push-changes.md)** - Reusable commit workflow

### Implementation References
- [Release Preparation Orchestrator](../workflows/release-preparation-orchestrator.yml) - Platform-level orchestration workflow
- [Approve Run Workflow](approve-run.md) - Reusable authorization workflow
- [Kitfox GitHub Infrastructure](https://github.com/folio-org/kitfox-github) - Centralized reusable workflows and actions
- [Universal Action: validate-team-membership](https://github.com/folio-org/kitfox-github/tree/master/.github/actions/validate-team-membership) - Team authorization
- [Reusable Workflow: release-preparation-flow.yml](https://github.com/folio-org/kitfox-github/blob/master/.github/workflows/release-preparation-flow.yml) - Core logic workflow
- [Reusable Workflow: release-preparation.yml](https://github.com/folio-org/kitfox-github/blob/master/.github/workflows/release-preparation.yml) - Public wrapper with notifications

---

**Status**: Production Ready  
**Maintained by**: Kitfox Team DevOps  
**Last Updated**: November 2025
**Implementation**: Fully Deployed Across FOLIO Ecosystem
