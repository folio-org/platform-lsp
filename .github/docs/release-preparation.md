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
│  ├─ Phase 2: Execution (Prepare Applications)           │
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
```

### Authorization Architecture

**Security Model**: Kitfox team-controlled initiation with distributed authorization

```yaml
# Team validation at orchestrator level (platform-lsp)
jobs:
  validate-actor:
    steps:
      - name: Validate Kitfox Team Membership
        uses: folio-org/kitfox-github/.github/actions/validate-team-membership@master
        with:
          username: ${{ github.actor }}
          team: kitfox
```

**Fallback Authorization**: Environment-based approval for non-team members
- **Environment**: "Eureka CI" 
- **Manual Approval**: Required for non-Kitfox team members
- **Audit Trail**: All approvals logged and tracked

### Distributed Workflow Architecture

The implementation uses a **proven distributed workflow architecture** with clear separation of concerns:

#### Layer 1: Orchestrator (platform-lsp)
- **Authorization**: Team validation and approval management
- **Discovery**: Application list extraction and merging
- **Orchestration**: Matrix coordination across all repositories
- **Aggregation**: Result collection and comprehensive reporting
- **Notification**: Platform-level success/failure reporting

#### Layer 2: Reusable Workflows (kitfox-github)
- **Pure Functionality**: No authorization logic - just execution
- **Universal Actions**: Shared composite actions for common operations
- **Standardized Templates**: Consistent patterns across all applications
- **Centralized Maintenance**: Single point of updates for shared logic

> 📚 **Detailed Documentation**: See [kitfox-github Workflow Implementation Guide](https://github.com/folio-org/kitfox-github/blob/master/.github/README.md) for comprehensive technical documentation of all reusable components and patterns.

#### Layer 3: Application Wrappers (app-* repositories)
- **Local Orchestration**: Application-specific workflow coordination
- **Parameter Passing**: Input forwarding to shared templates
- **Individual Notifications**: Application-level success/failure reporting

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

#### 2. orchestrate-external-workflow
```yaml
- uses: folio-org/kitfox-github/.github/actions/orchestrate-external-workflow@master
  with:
    repository: folio-org/${{ matrix.application }}
    workflow_file: release-preparation.yml
    workflow_parameters: |
      previous_release_branch: ${{ inputs.previous_release_branch }}
      new_release_branch: ${{ inputs.new_release_branch }}
      dry_run: ${{ inputs.dry_run }}
```

#### 3. collect-app-version
```yaml
- uses: folio-org/kitfox-github/.github/actions/collect-app-version@master
  with:
    app_name: ${{ matrix.application }}
    branch: ${{ inputs.new_release_branch }}
```

### Reusable Workflows Implementation

**Reusable Workflows** (folio-org/kitfox-github):

#### 1. release-preparation.yml
- **Purpose**: Individual application release branch preparation
- **Features**: Branch creation, version updates, descriptor modifications
- **Integration**: Called by all 31 application repositories

#### 2. release-preparation-notification.yml
- **Purpose**: Standardized Slack notification system
- **Features**: Success/failure reporting with detailed information
- **Integration**: Called by all application workflows for consistent messaging

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
  strategy:
    matrix:
      application: ${{ fromJson(needs.initial-check.outputs.applications) }}
    fail-fast: false    # Continue even if some apps fail
    max-parallel: 5     # Optimal resource utilization

  steps:
    - uses: folio-org/kitfox-github/.github/actions/orchestrate-external-workflow@master
      with:
        workflow_parameters: |
          dry_run: true  # Always validate first
```

#### Phase 2b: Execution (Prepare Applications)
```yaml
prepare-applications:
  needs: [check-applications]
  if: always() && needs.check-applications.result == 'success'
  strategy:
    matrix:
      application: ${{ fromJson(needs.initial-check.outputs.applications) }}
    fail-fast: false
    max-parallel: 5

  steps:
    - uses: folio-org/kitfox-github/.github/actions/orchestrate-external-workflow@master
      with:
        workflow_parameters: |
          previous_release_branch: ${{ inputs.previous_release_branch }}
          new_release_branch: ${{ inputs.new_release_branch }}
          dry_run: ${{ inputs.dry_run }}
```

### Phase 3: Result Collection & Aggregation

```yaml
collect-results:
  needs: [prepare-applications]
  if: always()
  
  steps:
    - name: Download All Results
      uses: actions/download-artifact@v4
      with:
        pattern: "app-result-*"
        merge-multiple: true
        
    - name: Aggregate Results with jq
      run: |
        success_count=0
        failure_count=0
        failed_apps=""
        
        for result_file in app-result-*.json; do
          if jq -e '.success' "$result_file" >/dev/null; then
            ((success_count++))
          else
            ((failure_count++))
            app_name=$(jq -r '.app_name' "$result_file")
            failed_apps="$failed_apps $app_name"
          fi
        done
        
        echo "success_count=$success_count" >> "$GITHUB_OUTPUT"
        echo "failure_count=$failure_count" >> "$GITHUB_OUTPUT"
        echo "failed_apps=$failed_apps" >> "$GITHUB_OUTPUT"
```

### Phase 4: Platform Preparation

```yaml
prepare-platform:
  needs: [collect-results]
  if: needs.collect-results.outputs.failure_count == '0'

  steps:
    - name: Update Platform Template
      run: |
        # Update platform.template.json with version constraints
        # Set application versions to ^FULL.VERSION (e.g., ^2.3.1)
        # Set eureka-components to ^VERSION placeholder
        # Upload as artifact

update-platform-config:
  needs: [initial-check, prepare-platform]
  steps:
    - name: Manage Update Config
      run: |
        # Create/update update-config.yml on default branch
        # Add new release branch to tracked branches
        # Use yq for reliable YAML manipulation

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
# Each matrix job uploads result artifact
- name: Upload Result
  uses: actions/upload-artifact@v4
  with:
    name: "app-result-${{ matrix.application }}"
    path: "result.json"

# Aggregation job downloads and processes all results
- name: Download All Results
  uses: actions/download-artifact@v4
  with:
    pattern: "app-result-*"

- name: Aggregate with jq
  run: |
    jq -s 'map(select(.success)) | length' *.json  # Success count
    jq -s 'map(select(.success | not) | .app_name) | join(" ")' *.json  # Failed apps
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
The release preparation process relies heavily on the shared infrastructure provided by kitfox-github. For detailed technical documentation on the reusable components:

- **[Workflow Implementation Guide](https://github.com/folio-org/kitfox-github/blob/master/.github/README.md)** - Entry point for all workflow documentation
- **[Application Release Preparation](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/app-release-preparation.md)** - Detailed guide to the individual application workflow
- **[Distributed Orchestration Patterns](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/distributed-orchestration.md)** - Cross-repository coordination architecture
- **[Security Implementation](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/security-implementation.md)** - Team authorization and access control patterns
- **[Application Notifications](https://github.com/folio-org/kitfox-github/blob/master/.github/docs/app-notification.md)** - Slack notification standards

### Implementation References
- [Release Preparation Workflow](../workflows/release-preparation-orchestrator.yml)
- [Kitfox GitHub Infrastructure](https://github.com/folio-org/kitfox-github)
- [Universal Action: validate-team-membership](https://github.com/folio-org/kitfox-github/tree/master/.github/actions/validate-team-membership)
- [Universal Action: orchestrate-external-workflow](https://github.com/folio-org/kitfox-github/tree/master/.github/actions/orchestrate-external-workflow)
- [Reusable Workflow: release-preparation](https://github.com/folio-org/kitfox-github/blob/master/.github/workflows/release-preparation.yml)

---

**Status**: Production Ready  
**Maintained by**: Kitfox Team DevOps  
**Last Updated**: October 2025
**Implementation**: Fully Deployed Across FOLIO Ecosystem
