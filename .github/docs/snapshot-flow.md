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
┌─────────────────────────────────────────────────────────┐
│                  SNAPSHOT FLOW ARCHITECTURE             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📦 MODULE LEVEL           🎯 APPLICATION LEVEL         │
│  ├─ Java Modules          ├─ App Descriptor Updates     │
│  │  ├─ Build & Test       │  ├─ Module Version Sync     │
│  │  ├─ Docker Image       │  ├─ Validation & Testing    │
│  │  ├─ Module Descriptor  │  └─ Snapshot Branch Update  │
│  │  └─ Artifact Publishing│                             │
│  │                        │                             │
│  └─ UI/Stripes Modules    │                             │
│     ├─ Node.js Build      │                             │
│     ├─ Test Execution     │                             │
│     ├─ NPM Publishing     │                             │
│     └─ Registry Update    │                             │
│                           │                             │
│  🏗️ PLATFORM LEVEL                                      │
│  ├─ Platform Descriptor Updates                         │
│  ├─ Application Version Sync                            │
│  ├─ Build & Validation                                  │
│  └─ Snapshot Environment Deployment                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
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

#### Application Snapshot Updates
*Based on [CI flow [snapshot] - Applications](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887193724/CI+flow+snapshot)*

**Trigger**: New module versions detected by scanning process

**Process Flow**:
1. **Version Detection**: Automated scanning identifies new module versions
2. **Descriptor Updates**: Application descriptors updated with latest module versions
3. **Validation Cycle**:
   - **Descriptor Validation**: JSON syntax and structure verification
   - **Build Testing**: Application composition validation
   - **Integration Testing**: Module compatibility verification
4. **Branch Update**: Snapshot branch updated with validated changes
5. **Notification**: Team notified of successful/failed updates

**Affected Repositories**: All 31 app-* repositories

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
- ✅ **Application Scanning**: Automated version detection and updates
- ✅ **Platform Synchronization**: Continuous platform state updates
- ✅ **Notification System**: Comprehensive team notifications

### Platform-LSP Snapshot Integration
- ✅ **Automated Scanning**: Platform continuously monitors for updates
- ✅ **Validation Pipeline**: Complete platform composition testing
- ✅ **Environment Sync**: Snapshot environment automatically updated
- ✅ **Team Notifications**: Slack integration for real-time updates

## 🔗 Related Documentation

- [Platform Architecture](../../README.md)
- [Eureka CI Flow [Snapshot]](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887193724/CI+flow+snapshot)

---

**Status**: Production Active  
**Maintained by**: Kitfox Team DevOps  
**Last Updated**: August 2025
