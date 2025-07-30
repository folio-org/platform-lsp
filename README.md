# platform-lsp

**FOLIO Platform Configuration & Release Orchestrator** - Central coordination repository for the FOLIO Library Services Platform.

## Overview

The `platform-lsp` repository serves as the **central orchestrator** for FOLIO's distributed ecosystem, managing platform configuration, application dependencies, and coordinated release operations across all FOLIO application repositories.

## 🎯 Key Responsibilities

- **🏗️ Platform Configuration**: Defines the complete FOLIO platform through `platform-descriptor.json`
- **🚀 Release Orchestration**: Coordinates release preparation across 30+ application repositories
- **📦 Application Management**: Manages application dependencies and version relationships
- **🔄 CI/CD Coordination**: Central entry point for distributed workflow operations
- **🛡️ Team Authorization**: Enforces Kitfox team permissions for critical operations

## 📁 Repository Structure

### Core Configuration Files

```
platform-lsp/
├── platform-descriptor.json     # Complete FOLIO platform definition
├── package.json                 # Node.js dependencies and build configuration  
├── yarn.lock                    # Exact dependency versions for reproducible builds
├── stripes.config.js           # Stripes framework configuration
├── stripes.modules.js          # Module loading configuration
├── platform-complete-install.json  # Full platform installation descriptor
└── .github/workflows/
    └── release-preparation.yml  # Central release orchestration workflow
```

### Platform Descriptor Structure

The `platform-descriptor.json` defines the complete FOLIO platform:

```json
{
  "name": "FOLIO LSP",
  "description": "FOLIO LSP (Library Services Platform)",
  "version": "R2-2025-SNAPSHOT.4803",
  "eureka-components": [
    {"name": "folio-kong", "version": "3.10.0-SNAPSHOT.16"},
    {"name": "folio-keycloak", "version": "26.3.0-SNAPSHOT.53"},
    {"name": "mgr-applications", "version": "4.0.0-SNAPSHOT.168"}
  ],
  "applications": {
    "required": [
      {"name": "app-platform-minimal", "version": "1.0.0-SNAPSHOT.4803"}
    ],
    "optional": [
      {"name": "app-erm-usage", "version": "1.0.0-SNAPSHOT.4803"}
    ]
  }
}
```

## 🏗️ Distributed Architecture Role

### Central Orchestrator Position

Platform-lsp serves as the **command center** for FOLIO's distributed CI/CD ecosystem:

```
                    ┌─────────────────────────────────────┐
                    │         platform-lsp                │
                    │      (Central Orchestrator)         │
                    ├─────────────────────────────────────┤
                    │ 🎯 release-preparation.yml          │
                    │   ├── Team Authorization            │
                    │   ├── Application Discovery         │
                    │   ├── Matrix Orchestration          │
                    │   └── Result Collection             │
                    └─────────────────┬───────────────────┘
                                      │
                    Universal Workflow Orchestration
                    (orchestrate-external-workflow)
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
  ┌──────────────┐              ┌────────────────┐           ┌──────────────┐
  │app-platform- │              │app-acquisitions│           │    app-*     │
  │   minimal    │              │                │           │   (30+)      │
  ├──────────────┤              ├────────────────┤           ├──────────────┤
  │ Wrapper      │              │ Wrapper        │     ...   │ Wrapper      │
  │ Workflow     │              │ Workflow       │           │ Workflow     │
  │      ▼       │              │      ▼         │           │      ▼       │
  │ Shared       │              │ Shared         │           │ Shared       │
  │ Template     │              │ Template       │           │ Template     │
  └──────────────┘              └────────────────┘           └──────────────┘
```

### Integration with kitfox-github

Uses [kitfox-github infrastructure actions](https://github.com/folio-org/kitfox-github) for:

- **🔒 Authorization**: `validate-team-membership` for Kitfox team access control
- **🚀 Orchestration**: `orchestrate-external-workflow` for distributed workflow coordination  
- **📊 Version Management**: `collect-app-version` for application version collection

## 🚀 Release Preparation Workflow (RANCHER-2320)

### Manual Trigger (Kitfox Team Only)

The release preparation workflow is manually triggered with specific parameters:

```yaml
# Trigger: workflow_dispatch
inputs:
  previous_release_branch: "R2-2024"      # Source release branch
  new_release_branch: "R1-2025"          # Target release branch  
  new_applications: "app-new1,app-new2"  # Optional new applications
  dry_run: true                          # Test mode (default)
```

### Workflow Execution Flow

1. **🛡️ Team Authorization**
   ```yaml
   - uses: folio-org/kitfox-github/.github/actions/validate-team-membership@main
     with:
       username: ${{ github.actor }}
       team: kitfox
   ```

2. **📋 Application Discovery**
   - Extracts applications from `platform-descriptor.json`
   - Merges with new applications if specified
   - Validates application repositories exist

3. **🎯 Distributed Orchestration**
   ```yaml
   - uses: folio-org/kitfox-github/.github/actions/orchestrate-external-workflow@main
     with:
       repository: folio-org/${{ matrix.application }}
       workflow_file: app-release-preparation.yml
       workflow_parameters: |
         previous_release_branch: ${{ inputs.previous_release_branch }}
         new_release_branch: ${{ inputs.new_release_branch }}
         dry_run: ${{ inputs.dry_run }}
   ```

4. **📊 Result Collection**
   - Monitors all application workflows for completion
   - Collects version information using `collect-app-version`
   - Generates summary of release preparation results

### Parallel Processing

- **Matrix Strategy**: Processes applications concurrently (max 5 parallel)
- **Fault Isolation**: Individual application failures don't block entire release
- **UUID Tracking**: Each workflow gets unique dispatch ID for monitoring

## 📦 Application Management

### Required vs Optional Applications

Applications are categorized in the platform descriptor:

- **Required**: Must be present in all FOLIO installations (e.g., `app-platform-minimal`)
- **Optional**: Installed based on institutional needs (e.g., domain-specific apps)

### Version Coordination

```json
{
  "applications": {
    "required": [
      {"name": "app-platform-minimal", "version": "1.0.0-SNAPSHOT.4803"}
    ],
    "optional": [
      {"name": "app-erm-usage", "version": "1.0.0-SNAPSHOT.4803"},
      {"name": "app-acquisitions", "version": "1.0.0-SNAPSHOT.4803"}
    ]
  }
}
```

### Eureka Components

Platform-specific infrastructure managed by platform-lsp:

- **folio-kong**: API gateway for request routing
- **folio-keycloak**: Authentication and authorization  
- **mgr-applications**: Application registry (FAR mode on AWS EKS)
- **mgr-tenants**: Tenant management services

## 🔄 CI/CD Integration Context

### Part of Eureka CI Ecosystem (RANCHER-2317)

Platform-lsp integrates with the broader FOLIO Eureka CI implementation:

- **🔄 Snapshot CI**: Automated module updates (RANCHER-2321/2322)
- **📦 Release CI**: Version management and release preparation (RANCHER-2323/2324)  
- **🗂️ Application Registry**: mgr-applications in FAR mode (RANCHER-2451)
- **🚀 Artifact Packaging**: Release tar.gz generation (RANCHER-2319)

### Branch Strategy Alignment

- **master**: Current stable release state
- **snapshot**: Latest development versions  
- **Release branches**: Named like `R1-2025`, `R2-2024` for specific releases
- **Feature branches**: Jira ticket naming (`RANCHER-XXXX`)

## 🛡️ Team Authorization & Security

### Kitfox Team Control

All critical platform operations require **Kitfox team membership**:

- ✅ **Release Preparation**: Only Kitfox team can trigger release workflows
- ✅ **Platform Configuration**: Changes to platform descriptor require team approval  
- ✅ **Infrastructure Operations**: Platform deployment and configuration
- 🔍 **Audit Trail**: All operations logged with team member identification

### Security Implementation

```yaml
# Authorization check at workflow start
jobs:
  authorize:
    outputs:
      authorized: ${{ steps.team-check.outputs.authorized }}
    steps:
      - name: Validate Kitfox Team Membership
        id: team-check
        uses: folio-org/kitfox-github/.github/actions/validate-team-membership@main
        
  release-preparation:
    needs: authorize
    if: needs.authorize.outputs.authorized == 'true'
    # ... protected operations
```

## 📋 Usage Examples

### Triggering Release Preparation

**1. Standard Release Preparation**
```bash
# Via GitHub UI: Actions → Release Preparation → Run workflow
# Parameters:
#   previous_release_branch: "R2-2024"
#   new_release_branch: "R1-2025"  
#   dry_run: true (for testing)
```

**2. Adding New Applications**
```bash
# Parameters:
#   previous_release_branch: "R2-2024"
#   new_release_branch: "R1-2025"
#   new_applications: "app-new-feature,app-experimental"
#   dry_run: false (for actual release)
```

### Local Development

**Platform Descriptor Validation**
```bash
# Validate JSON syntax
jq . platform-descriptor.json

# Check application versions exist
jq -r '.applications.required[].name' platform-descriptor.json
```

**Stripes Configuration Testing**
```bash
# Install dependencies
yarn install

# Validate Stripes configuration  
yarn stripes build --analyze
```

## 🔮 Future Enhancements

### Planned Integrations

Based on RANCHER-2317 epic roadmap:

| **Feature** | **Status** | **Description** |
|-------------|------------|-----------------|
| **Automated Scanning** | 🔄 Planned | Regular checks for module updates (RANCHER-2321/2322) |
| **Release Artifacts** | 📋 Blocked | tar.gz packaging of complete platform (RANCHER-2319) |
| **Registry Integration** | 🚧 In Progress | Direct mgr-applications integration (RANCHER-2451) |

### Evolution Principles

- **📊 Data-Driven**: Platform changes based on usage analytics
- **🛡️ Security-First**: All enhancements maintain team authorization
- **⚡ Performance**: Optimize for distributed workflow efficiency
- **📚 Documentation**: Clear documentation for all platform changes

## 🤝 Contributing

### Making Platform Changes

1. **🎫 Create Feature Branch**: Use Jira ticket name (`RANCHER-XXXX`)
2. **🔍 Impact Assessment**: Consider effects on all application repositories
3. **🧪 Test Changes**: Use `dry_run: true` for validation
4. **👥 Team Review**: Include Kitfox team members in all PRs
5. **📋 Documentation**: Update README and platform documentation

### Platform Descriptor Updates

```bash
# 1. Validate JSON syntax
jq . platform-descriptor.json

# 2. Test application version compatibility
./scripts/validate-app-versions.sh

# 3. Create PR with clear description of changes
# 4. Request Kitfox team review
# 5. Test in snapshot environment before merge
```

### Required Reviewers

- **Kitfox Team**: Always required for platform changes
- **@NikitaSedyx**: Required for application-related changes
- **Platform Teams**: For changes affecting specific domains

## 🎯 Platform Mission

Platform-lsp enables **FOLIO's distributed library management vision** by:

- **🏗️ Centralizing Configuration**: Single source of truth for platform state
- **🚀 Enabling Scale**: Coordinated operations across 30+ applications  
- **🛡️ Ensuring Security**: Team-based authorization for critical operations
- **⚡ Optimizing Performance**: Parallel processing with fault isolation
- **📊 Maintaining Quality**: Automated validation and testing integration

*Supporting libraries worldwide with flexible, robust, and secure digital infrastructure.*

---

**Quick Links**: [Release Workflow](/.github/workflows/release-preparation.yml) | [Platform Descriptor](/platform-descriptor.json) | [Kitfox Actions](https://github.com/folio-org/kitfox-github) | [FOLIO Documentation](https://wiki.folio.org)