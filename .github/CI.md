# FOLIO Eureka CI/CD Process Documentation

**Central documentation for the FOLIO Eureka Continuous Integration and Delivery workflows**

This repository implements the **FOLIO Eureka CI/CD ecosystem** as the central orchestrator for platform state management and automated release processes. The Eureka CI process consists of three key pillars that ensure continuous integration, automated testing, and coordinated releases across the entire FOLIO ecosystem.

## 🏗️ Eureka CI Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                 EUREKA CI ECOSYSTEM                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  🔄 SNAPSHOT FLOW        📋 RELEASE PREP     🚀 RELEASE    │
│  Continuous Integration  Coordination        Final Build   │
│                                                            │
│  ├─ Module Updates       ├─ Branch Creation   ├─ Artifact  │
│  ├─ Application Sync     ├─ Version Alignment ├─ Registry  │
│  └─ Platform Refresh     └─ Cross-repo Coord  └─ Tagging   │
│                                                            │
└────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
                    ▼           ▼           ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │   Modules   │ │ Applications│ │  Platform   │
            │   (backend) │ │   (31 apps) │ │ (platform-  │
            │    UI       │ │             │ │     lsp)    │
            │    edge)    │ │             │ │             │
            └─────────────┘ └─────────────┘ └─────────────┘
```

## 📚 Three Pillars of Eureka CI

### 1. 🔄 [Snapshot Flow - Continuous Integration](docs/snapshot-flow.md)

**Purpose**: Automated continuous integration for ongoing development

The snapshot flow handles the continuous integration of daily development work, ensuring that every code change across modules, applications, and the platform is automatically built, tested, and integrated into the snapshot environment.

**Key Processes**:
- **Module CI**: Backend, edge and UI/Stripes module builds
- **Application Sync**: Automatic application descriptor updates via orchestrated workflows
- **Platform Refresh**: Continuous platform state updates with parallel processing
- **Version Management**: SNAPSHOT version increments and build IDs
- **Orchestrated Updates**: Platform-LSP coordinates updates across 31+ application repositories

**Key Workflows**:
- **`snapshot-update-orchestrator.yml`**: Platform-LSP orchestrator for application snapshot updates
- **`snapshot-update-flow.yml`**: Individual application update workflow (kitfox-github)

**Documentation**: [📖 Detailed Snapshot Flow Guide](docs/snapshot-flow.md)

---

### 2. 📋 [Release Preparation - Coordinated Release Management](docs/release-preparation.md)

**Purpose**: Orchestrated preparation of release branches across the entire FOLIO ecosystem

The release preparation process coordinates the creation of release branches, version alignment, and cross-repository synchronization to prepare the entire FOLIO platform for an official release.

**Key Processes**:
- **Branch Orchestration**: Automated creation of release branches across 31+ repositories
- **Version Coordination**: Alignment of component and application versions
- **Distributed Workflows**: Parallel processing with comprehensive monitoring

**Documentation**: [📖 Detailed Release Preparation Guide](docs/release-preparation.md)

---

### 3. 🚀 [Release Flow - Final Artifact Creation](docs/release-flow.md)

**Purpose**: Production of final release artifacts from prepared release branches

The release flow takes the prepared release branches and produces the final consumable artifacts for FOLIO releases, including official Docker images, Maven artifacts, NPM packages, and platform bundles.

**Key Processes**:
- **Module Releases**: Final module artifact creation and publishing
- **Application Publishing**: Release application descriptors to registries
- **Platform Artifacts**: Complete platform bundle generation
- **Registry Updates**: Official artifact deployment to production repositories

**Documentation**: [📖 Detailed Release Flow Guide](docs/release-flow.md)

---

## 🎯 Platform-LSP Role in Eureka CI

As the **central orchestrator**, `platform-lsp` plays a critical role in each CI pillar:

### Snapshot Flow Integration
- **Automatic Updates**: Receives latest application and component versions
- **Validation**: Ensures platform compatibility with new snapshots
- **Environment Sync**: Keeps snapshot environments current

### Release Preparation Leadership
- **Orchestration**: Initiates and coordinates release preparation across all repositories
- **Monitoring**: Tracks progress and aggregates results from distributed workflows
- **State Management**: Maintains authoritative platform state during transitions

### Release Flow Coordination
- **Artifact Generation**: Produces final platform release bundles
- **Version Tagging**: Creates official release tags and artifacts
- **Registry Publishing**: Deploys platform artifacts to production repositories

## 🚦 CI Flow States and Triggers

### Trigger Matrix

| **Flow** | **Trigger** | **Frequency** | **Scope** | **Authorization** |
|----------|-------------|---------------|-----------|------------------|
| **Snapshot** | Code Push | Continuous | Per-module/app | Automatic |
| **Release Prep** | Manual | Per-release | Platform-wide | Kitfox Team |
| **Release** | Tag Creation | Per-release | Per-component | Automatic |

### Platform State Transitions

```
Development Cycle:
snapshot → release-prep → release-branch → tagged-release → master

Version Evolution:
1.0.0-SNAPSHOT.xxx → 1.0.0-RC → 1.0.0 → master-baseline
```

## 🛠️ Implementation Architecture

### Distributed Workflow System

The platform-lsp implements a **proven distributed workflow architecture**:

- **Universal Actions**: Shared composite actions for authorization, orchestration, and version management
- **Reusable Workflows**: Centralized workflow templates for consistent processing
- **Matrix Processing**: Parallel execution across 31+ application repositories
- **Result Aggregation**: Comprehensive monitoring and failure reporting
- **Dual Notifications**: Platform-level and individual component notifications

### Technology Stack

- **GitHub Actions**: Primary CI/CD engine
- **Composite Actions**: Reusable workflow components
- **Matrix Strategies**: Parallel repository processing
- **Artifact Management**: Cross-job data persistence
- **Slack Integration**: Comprehensive notification system

## 📋 Quick Navigation

### Primary Documentation
- [🔄 Snapshot Flow Documentation](docs/snapshot-flow.md)
- [📋 Release Preparation Documentation](docs/release-preparation.md)
- [🚀 Release Flow Documentation](docs/release-flow.md)

### Implementation References
- [⚙️ Workflow Configuration](../.github/workflows/)
- [📄 Platform Descriptor](../platform-descriptor.json)
- [🏗️ Repository Architecture](../README.md)

### External References
- [Eureka CI Flow [Snapshot]](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887193724/CI+flow+snapshot)
- [Eureka CI Flow [Release]](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887488514/CI+flow+release)
- [Release Preparation Process](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/886178625/Release+preparation)
- [Eureka Namespace Architecture](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/156368911/Eureka+Namespace+Architecture)

---

**Maintained by**: Kitfox Team DevOps  
**Last Updated**: August 2025  
**Status**: Production Ready

*This documentation serves as the definitive guide for understanding and implementing FOLIO Eureka CI/CD processes.*
