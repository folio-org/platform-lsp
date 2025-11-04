# Snapshot Flow - Continuous Integration

**Automated continuous integration for ongoing FOLIO development**

The Snapshot Flow is the backbone of daily development integration in the FOLIO Eureka ecosystem. It ensures that every code commit across modules, applications, and the platform triggers automated builds and keeps snapshot artifacts continuously available for testing.

## 🎯 Purpose and Scope

The Snapshot Flow handles continuous integration of ongoing development (snapshot builds), ensuring that:

- **Every commit** triggers automated build and test cycles
- **Snapshot artifacts** are continuously available for testing environments
- **Dependencies** are automatically updated across the ecosystem
- **Integration issues** are detected early in the development cycle

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                  SNAPSHOT FLOW ARCHITECTURE              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  📦 MODULE LEVEL           🎯 APPLICATION LEVEL         │
│  ├─ Java Modules          ├─ Orchestrated Updates        │
│  │  ├─ Build & Test       │  ├─ Platform-LSP Trigger     │
│  │  ├─ Docker Image       │  ├─ Matrix Processing        │
│  │  ├─ Module Descriptor  │  │  ├─ 31+ Apps Parallel     │
│  │  └─ Artifact Publishing│  │  ├─ Fail-Safe Execution   │
│  │                        │  │  └─ Result Aggregation    │
│  └─ UI/Stripes Modules    │  ├─ Individual App Updates   │
│     ├─ Node.js Build      │  │  ├─ Module Version Sync   │
│     ├─ Test Execution     │  │  ├─ Validation & Testing  │
│     ├─ NPM Publishing     │  │  └─ Snapshot Branch Update│
│     └─ Registry Update    │  └─ Comprehensive Reporting  │
│                           │                              │
│  🏗️ PLATFORM LEVEL                                       │
│  ├─ Application Discovery (platform-descriptor.json)     │
│  ├─ Distributed Workflow Orchestration                   │
│  ├─ Cross-Repository Authorization                       │
│  ├─ Success/Failure Monitoring                           │
│  └─ Slack Notification System                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## 🔄 Snapshot Flow Components

### 1. Module Flows

#### Java-Based Modules
*Based on [CI flow [snapshot] - Java modules](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887193724/CI+flow+snapshot)*

**Trigger**: Code push to module repository (mod-*, edge-*)

**Process Flow**:
1. **GitHub Trigger**: Commit pushed to main/master branch
2. **Jenkins/GitHub Actions Execution**:
   - **Build & Test**: Maven-based compilation and testing
   - **Docker Image Build**: Containerization of the module
   - **Module Descriptor Generation**: API and interface definitions
3. **Artifact Publishing**:
   - **Maven Repository**: Snapshot JAR artifacts
   - **Docker Hub**: Container images with snapshot tags
   - **FOLIO Registry**: Module descriptor registration

**Version Pattern**: `x.y.z-SNAPSHOT.buildId`
- `x.y.z`: Semantic version base
- `buildId`: Incremental build identifier

#### UI/Stripes Modules
*Based on [CI flow [snapshot] - UI modules](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887193724/CI+flow+snapshot)*

**Trigger**: Code push to UI module repository (ui-*)

**Process Flow**:
1. **GitHub Trigger**: Commit pushed to main/master branch
2. **GitHub Actions Execution**:
   - **Build & Test**: Node.js/Yarn compilation and testing
   - **Module Descriptor Generation**: UI module capabilities and dependencies
3. **Artifact Publishing**:
   - **NPM Repository (npm-folio)**: Snapshot NPM packages
   - **FOLIO Registry**: Module descriptor registration

### 2. Application Flows

#### Application Snapshot Updates - Platform Orchestrator
*Implemented via `application-update-orchestrator.yml` workflow in platform-lsp*

**Trigger**: Scheduled execution (every 20 minutes) or manual workflow dispatch

**Authorization**: Kitfox team members or approved environment access

**Process Flow**:
1. **Actor Validation**:
   - Generate GitHub App token for cross-repository access
   - Validate team membership (Kitfox team) or require environment approval
2. **Application Discovery**:
   - Extract application list from platform-descriptor.json (snapshot branch)
   - Identify all app-* repositories (required + optional applications)
   - Merge with configuration from each application's `update-config.yml`
3. **Configuration-Based Updates**:
   - **Configuration Reading**: Each application's `update-config.yml` defines update behavior
   - **Matrix Building**: Combine all enabled branches from all applications into unified matrix
   - **Parallel Processing**: Process all application branches concurrently (max 10 parallel)
   - **Individual Workflows**: Each application branch triggers `application-update-flow.yml` from kitfox-github
   - **Fail-Safe Processing**: Continue processing other apps even if some fail
4. **Result Collection**:
   - Download and analyze results from all application workflows
   - Categorize outcomes: success, failure, updated applications
   - Generate comprehensive reports with specific reasons
5. **Slack Notifications**:
   - **Success**: Report updated application count and total processed
   - **Failure**: Detailed failure reasons and affected applications
   - **Channel**: Configurable Slack channel for team notifications

**Affected Repositories**: All 31+ app-* repositories processed in parallel

**Key Features**:
- **Configuration-Driven**: Each application controls its update behavior via `update-config.yml`
- **Unified Architecture**: Same workflow handles snapshot and release branches
- **Distributed Processing**: Matrix strategy for concurrent updates
- **Authorization Separation**: Team validation in orchestrator, pure functionality in workers
- **Comprehensive Monitoring**: Detailed success/failure tracking and reporting

### 3. Platform Flow

#### Platform Snapshot Synchronization
*Based on [CI flow [snapshot] - Platform](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887193724/CI+flow+snapshot)*

**Trigger**: New application versions detected by scanning process

**Process Flow**:
1. **Version Detection**: Platform scanning identifies new application and eureka-component versions
2. **Platform Descriptor Update**: `platform-descriptor.json` updated with latest versions
3. **Validation Process**:
   - **JSON Validation**: Platform descriptor syntax verification
   - **Dependency Resolution**: Application and component compatibility checks
   - **Build Testing**: Complete platform composition validation
4. **Environment Update**: Snapshot environment refreshed with new platform state
5. **Notification**: Platform team notified of updates

## 📊 Versioning Strategy

### Build ID Management

The snapshot flow uses incremental Build IDs to track continuous updates:

```
Component Evolution:
mod-example: 1.2.0-SNAPSHOT.150 → 1.2.0-SNAPSHOT.151
app-example: 1.0.0-SNAPSHOT.75  → 1.0.0-SNAPSHOT.76
platform:   R2-2025-SNAPSHOT.4803 → R2-2025-SNAPSHOT.4804
```

### Version Propagation Flow

```
Module Update → Application Update → Platform Update
     ↓                ↓                   ↓
Build ID++       Build ID++         Build ID++
     ↓                ↓                   ↓
Registry        App Descriptor     Platform Descriptor
  Update           Update              Update
```

## 🔍 Scan Mechanisms

### Automated Scanning Process

**Module Scanning**: Applications continuously monitor module registries for new versions
**Application Scanning**: Platform monitors application registries for new versions
**Frequency**: Continuous/scheduled scanning based on configured intervals

### Scan Flow Implementation

1. **Registry Query**: Check FOLIO registry for new artifact versions
2. **Version Comparison**: Compare current vs. available versions
3. **Update Decision**: Determine if updates are needed
4. **Pull Request Creation**: Automated PR creation for version updates
5. **Validation Pipeline**: Automated testing and validation
6. **Auto-Merge**: Successful validations can trigger automatic merges

## 🧪 Testing and Validation

### Module-Level Testing
- **Unit Tests**: Comprehensive module functionality testing
- **Integration Tests**: Module interface and dependency testing
- **Container Testing**: Docker image validation and security scanning

### Application-Level Testing
- **Descriptor Validation**: Application composition verification
- **Module Compatibility**: Inter-module dependency resolution
- **Performance Testing**: Application-level performance benchmarks

### Platform-Level Testing
- **Complete Platform Build**: Full platform composition validation
- **Environment Deployment**: Snapshot environment refresh testing
- **End-to-End Testing**: Complete workflow validation

## 🚨 Failure Handling

### Module Build Failures
- **Immediate Notification**: Development team alerted
- **Build Status Reporting**: GitHub status checks updated
- **Artifact Rollback**: Previous stable version maintained

### Application Update Failures
- **Snapshot Branch Protection**: Failed updates don't enter snapshot branch
- **Detailed Error Reporting**: Specific module conflicts identified
- **Team Notifications**: Application maintainers notified of issues

### Platform Integration Failures
- **Platform State Protection**: Invalid states prevented from deployment
- **Comprehensive Logging**: Detailed failure analysis provided
- **Escalation Process**: Critical failures escalated to platform team

## 📈 Monitoring and Metrics

### Key Performance Indicators
- **Build Success Rate**: Percentage of successful module builds
- **Integration Velocity**: Time from commit to snapshot availability
- **Test Coverage**: Automated test execution metrics
- **Deployment Frequency**: Snapshot environment update frequency

### Monitoring Tools
- **GitHub Actions**: Build and test execution monitoring
- **Jenkins**: Legacy module build monitoring
- **FOLIO Registry**: Artifact availability tracking
- **Slack Notifications**: Real-time team notifications

## 🔧 Implementation Status

### Current Implementation
- ✅ **Module CI**: Both Java and UI module flows operational
- ✅ **Application Orchestration**: Platform-LSP coordinates updates across all applications
- ✅ **Distributed Processing**: Parallel matrix strategy for 31+ repositories
- ✅ **Authorization Framework**: Team-based access control with environment fallback
- ✅ **Comprehensive Monitoring**: Success/failure tracking with detailed reporting
- ✅ **Notification System**: Slack integration with rich status reporting

### Platform-LSP Snapshot Integration
- ✅ **Unified Architecture**: `application-update-orchestrator.yml` handles all application updates
- ✅ **Configuration-Driven**: Each application defines update behavior via `update-config.yml`
- ✅ **Matrix Processing**: Concurrent processing with fail-safe mechanisms
- ✅ **Result Aggregation**: Comprehensive success/failure analysis and reporting
- ✅ **Team Notifications**: Rich Slack notifications with detailed status information

## 🔗 Related Documentation

### Platform Documentation
- [Platform Architecture](../../README.md)
- [Eureka CI Overview](../CI.md)

### Workflow Implementation
- [Application Update Orchestrator](application-update-orchestrator.md) - Configuration-driven application update orchestrator
- [`application-update-flow.yml`](../../kitfox-github/.github/docs/application-update-flow.md) - Individual application update flow

### External References
- [Eureka CI Flow [Snapshot]](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887193724/CI+flow+snapshot)
- [FOLIO Application Registry (FAR)](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/1115029566/Application+registry+hosting+approach)

---

**Status**: Production Active
**Maintained by**: Kitfox Team DevOps
**Last Updated**: November 2025
