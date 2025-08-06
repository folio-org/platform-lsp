# platform-lsp

**FOLIO Eureka Platform State Repository** - Central source of truth for FOLIO Library Services Platform configuration and component orchestration.

## Overview

The `platform-lsp` repository maintains the **definitive state** of the FOLIO Eureka platform, serving as the single source of truth for platform composition, component versions, and deployment configuration. This repository enables consistent platform deployments across environments by defining all required components, applications, and their exact versions.

## 🏗️ Eureka Platform Architecture

The FOLIO Eureka deployment represents a sophisticated microservices architecture with enhanced features compared to traditional FOLIO deployments:

### Core Infrastructure Components

**Eureka-Specific Components (Stateful/Daemon Sets):**
- **🔐 Keycloak**: Authentication and authorization service (Stateful-set)
- **🌐 Kong**: API gateway and traffic management (Daemon-set)  
- **📋 mgr-applications**: Application registry and management (Replica-set)
- **🏢 mgr-tenants**: Tenant lifecycle management
- **🔗 mgr-tenant-entitlements**: Tenant permission management
- **🔧 folio-module-sidecar**: Service discovery and proxy sidecars

**Platform Services:**
- **🗄️ PostgreSQL**: Primary data storage with multiple databases (Stateful-set)
- **🔍 OpenSearch**: Search and analytics engine (Stateful-set)
- **📨 Kafka**: Event streaming and messaging platform (Stateful-set)

### Application Layer

The platform orchestrates **31 application repositories**, each containing domain-specific modules:

```
┌─────────────────────────────────────┐
│         platform-lsp                │
│    (Platform State Definition)      │
│                                     │
│  📄 platform-descriptor.json        │
│  📦 package.json & yarn.lock        │
│  ⚙️  stripes.config.js              │
│  🔧 stripes.modules.js              │
└─────────────────┬───────────────────┘
                  │
        Platform State Coordination
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│app-*    │  │app-*    │  │app-*    │
│(31 apps)│  │(domain) │  │(modules)│
└─────────┘  └─────────┘  └─────────┘
```

## 📄 Platform Descriptor Structure

The `platform-descriptor.json` is the **core artifact** defining the complete platform state:

### Platform Metadata
```json
{
  "name": "Platform LSP",
  "description": "FOLIO Library Services Platform - Eureka Implementation",
  "version": "R2-2025-SNAPSHOT.4803"
}
```

### Eureka Infrastructure Components
```json
"eureka-components": [
  {"name": "folio-kong", "version": "3.10.0-SNAPSHOT.16"},
  {"name": "folio-keycloak", "version": "26.3.0-SNAPSHOT.53"},
  {"name": "folio-module-sidecar", "version": "2.0.6"},
  {"name": "mgr-applications", "version": "4.0.0-SNAPSHOT.168"},
  {"name": "mgr-tenants", "version": "2.0.1"},
  {"name": "mgr-tenant-entitlements", "version": "2.0.8"}
]
```

### Application Definitions
```json
"applications": {
  "required": [
    {"name": "app-platform-minimal", "version": "1.0.0-SNAPSHOT.4803"},
    {"name": "app-platform-complete", "version": "1.0.0-SNAPSHOT.4808"}
  ],
  "optional": [
    {"name": "app-erm-usage", "version": "1.0.0-SNAPSHOT.4803"},
    {"name": "app-acquisitions", "version": "1.0.0-SNAPSHOT.4803"},
    {"name": "app-consortia", "version": "1.1.0-SNAPSHOT.4803"}
  ]
}
```

### Infrastructure Dependencies
```json
"dependencies": {
  "postgres": ">=16.0",
  "kafka": ">=2.8.0", 
  "opensearch": ">=1.0.0"
}
```

## 🌿 Branch Strategy & Platform States

### Platform State Correlation

Each branch represents a specific **platform state** with different purposes:

| **Branch** | **Platform State** | **Purpose** | **Component Versions** |
|------------|-------------------|-------------|----------------------|
| **`master`** | **Current Stable Release** | Production-ready state | Latest stable release versions |
| **`snapshot`** | **Latest Development** | Active development state | Latest SNAPSHOT versions |
| **`R1-2025`** | **Specific Release** | Tagged release state | Fixed release versions (e.g., 1.2.0) |
| **`R2-2024`** | **Previous Release** | Historical release state | Previous release versions |

### Branch Lifecycle

```
Development Flow:
snapshot → (development) → Rx-YYYY (release preparation) → master (stable)

Version Evolution:
1.0.0-SNAPSHOT.xxx → 1.0.0 → 1.1.0-SNAPSHOT.xxx → 1.1.0
```

### State Transitions

- **Snapshot → Release**: Component versions change from `SNAPSHOT` to fixed versions
- **Release → Master**: Stable release state becomes current production baseline
- **Master → Next Snapshot**: New development cycle begins with incremented SNAPSHOT versions

## 🔄 Eureka CI Flow Integration

The platform-lsp repository is central to the **Eureka CI flow** as documented in the [CI flow [release]](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887488514/CI+flow+release):

### Scan Flow (Automated)
- **Purpose**: Continuously monitor for component updates
- **Trigger**: Scheduled/automated
- **Action**: Updates platform descriptor with latest available versions
- **Output**: Pull requests with version updates

### Pull Request Update Flow
- **Purpose**: Validate platform descriptor changes
- **Trigger**: PR creation/update
- **Action**: Runs validation, builds, and tests
- **Output**: Validated platform state or failure notifications

### Pull Request Merge Flow  
- **Purpose**: Finalize platform state updates
- **Trigger**: PR approval and merge
- **Action**: Commits new platform state, creates tags
- **Output**: Updated platform releases and notifications

### Release Preparation Flow
- **Purpose**: Coordinate release across all applications
- **Trigger**: Manual (Kitfox team)
- **Action**: Creates release branches and coordinates application updates
- **Output**: Complete platform release preparation

## 📦 Release Artifacts

When creating platform releases, **tar.gz archives** are generated containing the complete platform state as described in [Artifacts [release]](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/889389109/Artifacts+release):

### Archive Contents
- **`platform-descriptor.json`**: Complete platform definition
- **Application descriptors folder**: All application compositions
- **`package.json` & `yarn.lock`**: Frontend dependency management
- **`stripes.config.js` & `stripes.modules.js`**: Stripes framework configuration

### Release Versioning
```
Platform Release: R2-2025.1
├── Eureka Components: Fixed versions (e.g., kong-3.10.0)
├── Applications: Fixed versions (e.g., app-platform-minimal-1.0.0)
└── Dependencies: Minimum required versions
```

## 🏗️ Platform Management

### Component Categories

**Required Applications**: Must be present in all FOLIO installations
- `app-platform-minimal`: Core FOLIO functionality
- `app-platform-complete`: Extended platform features

**Optional Applications**: Installed based on institutional needs
- Domain-specific applications (ERM, Acquisitions, etc.)
- Specialized workflow applications
- Integration applications (Edge services)

**Infrastructure Components**: Eureka-specific enhancements
- Authentication (Keycloak)
- API Gateway (Kong) 
- Application Management (mgr-applications)
- Service Discovery (sidecar)

## 🤝 Contributing

### Making Platform Changes

1. **🎫 Create Feature Branch**: Use Jira ticket name (`RANCHER-XXXX`)
2. **🔍 Impact Assessment**: Consider effects across all platform components
3. **📋 Update Platform Descriptor**: Modify component versions as needed
4. **🧪 Test Changes**: Validate platform composition and dependencies

## 🎯 Platform Mission

Platform-lsp enables **FOLIO's Eureka implementation** by:

- **🏗️ Centralizing Platform State**: Single source of truth for complete platform composition
- **⚡ Enabling Eureka Features**: Orchestrates enhanced microservices architecture with sidecars, Kong, and Keycloak
- **🔄 Supporting CI/CD**: Integrates with automated scanning, validation, and release processes
- **📦 Ensuring Consistency**: Provides reproducible platform deployments through versioned artifacts
- **🛡️ Maintaining Security**: Team-based authorization for critical platform operations

---

**Quick Links**: 
- [Platform Descriptor](/platform-descriptor.json) 
- [Eureka Architecture](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/156368911/Eureka+Namespace+Architecture)
- [CI Flow Documentation](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887488514/CI+flow+release)
- [Release Artifacts](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/889389109/Artifacts+release)
- [FOLIO Documentation](https://wiki.folio.org)