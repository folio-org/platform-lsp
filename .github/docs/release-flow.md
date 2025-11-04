# Release Flow - Final Artifact Creation

**Production of final release artifacts from prepared release branches**

The Release Flow represents the final stage of the FOLIO Eureka CI/CD pipeline, transforming prepared release branches into production-ready artifacts. This process ensures that validated release code is compiled, tested, and published as official FOLIO release components.

## 🎯 Purpose and Scope

The Release Flow produces final consumable artifacts for FOLIO releases by:

- **Building final artifacts** from prepared release branches and tags
- **Publishing official releases** to production artifact repositories
- **Creating stable versions** with proper semantic versioning
- **Ensuring artifact integrity** through comprehensive validation
- **Enabling deployment** of official FOLIO releases

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                 RELEASE FLOW ARCHITECTURE               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📦 MODULE RELEASES        🎯 APPLICATION RELEASES      │
│  ├─ Tag-Triggered Builds   ├─ Descriptor Publishing     │
│  │  ├─ Release Validation  │  ├─ Registry Updates       │
│  │  ├─ Artifact Creation   │  ├─ Version Tagging        │
│  │  ├─ Registry Publishing │  └─ Notification System    │
│  │  └─ Version Tagging     │                            │
│  │                         │                            │
│  └─ Production Deployment  │                            │
│     ├─ Docker Hub          │                            │
│     ├─ Maven Central       │                            │
│     ├─ NPM Registry        │                            │
│     └─ FOLIO Registry      │                            │
│                            │                            │
│  🏗️ PLATFORM RELEASES                                   │
│  ├─ Complete Bundle Generation                          │
│  ├─ Artifact Archive Creation                           │
│  ├─ Registry Publishing                                 │
│  └─ Release Tag Management                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Release Flow Components

### 1. Module Release Flows

#### Java Module Releases
*Based on [CI flow [release] - Modules](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887488514/CI+flow+release)*

**Trigger**: Version tag creation (e.g., `v1.2.0`)

**Process Flow**:
1. **Tag Detection**: GitHub tag creation triggers release workflow
2. **Release Branch Validation**: Ensures release branch exists and is properly prepared
3. **Final Build Process**:
   - **Maven Release Build**: Clean compilation with release profile
   - **Comprehensive Testing**: Full test suite execution
   - **Security Scanning**: Vulnerability and compliance checks
   - **Documentation Generation**: API docs and release notes
4. **Artifact Creation**:
   - **Release JAR**: Non-SNAPSHOT Maven artifact
   - **Docker Image**: Production container with release tag
   - **Module Descriptor**: Final API specification
5. **Publishing Pipeline**:
   - **Maven Central**: Official Java artifact repository
   - **Docker Hub**: Production container registry
   - **FOLIO Registry**: Module descriptor publishing
6. **Release Finalization**:
   - **GitHub Release**: Official release creation with notes
   - **Tag Verification**: Ensure proper tag association
   - **Notification**: Team and stakeholder notifications

**Version Pattern**: `x.y.z` (semantic versioning without SNAPSHOT)

#### UI/Stripes Module Releases
*Based on [CI flow [release] - Modules](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887488514/CI+flow+release)*

**Trigger**: Version tag creation (e.g., `v2.1.0`)

**Process Flow**:
1. **Tag Detection**: GitHub tag creation triggers release workflow
2. **Release Validation**: Release branch and version consistency checks
3. **Production Build**:
   - **Node.js Build**: Optimized production compilation
   - **Test Execution**: Complete UI test suite
   - **Bundle Optimization**: Minification and optimization
   - **Accessibility Testing**: WCAG compliance validation
4. **Artifact Generation**:
   - **NPM Package**: Production-ready UI module
   - **Module Descriptor**: UI capabilities and dependencies
5. **Publishing Process**:
   - **NPM Registry**: Official NPM package publication
   - **FOLIO Registry**: UI module descriptor registration
6. **Release Documentation**:
   - **Change Log**: Automated changelog generation
   - **GitHub Release**: Official release with artifacts
   - **Team Notification**: Release completion alerts

### 2. Application Release Flows

#### Application Descriptor Publishing
*Based on [CI flow [release] - Applications](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887488514/CI+flow+release)*

**Process Components**:

##### Configuration-Driven Updates
- **Update Configuration**: Each application's `update-config.yml` defines release branch update behavior
- **Orchestrated Scanning**: Platform orchestrator triggers updates based on configuration
- **PR-Based Workflow**: Release branches use pull request workflow for review
- **Version Filtering**: Release-only module versions (`pre_release: 'false'`)

##### Pull Request Update Flow
**Trigger**: Application update orchestrator or scheduled execution

**Process**:
1. **Module Version Discovery**: Query FOLIO registry for release-only module versions
2. **Application Descriptor Update**: Update with new stable module versions
3. **Validation Pipeline**:
   - **Descriptor Generation**: Maven-based descriptor creation
   - **Interface Validation**: Module interface integrity checks via FAR
   - **Dependency Validation**: Platform descriptor-based dependency verification
4. **Pull Request Management**:
   - **PR Creation/Update**: Automated PR creation or update with changes
   - **Reviewer Assignment**: Configured team reviewers assigned
   - **Label Application**: Automated labels for tracking
5. **Status Reporting**: Comprehensive validation results and notifications

##### Pull Request Merge Flow
**Trigger**: PR approval and merge to release branch

**Process**:
1. **Final Validation**: Release PR check validates changes
2. **Merge Completion**: Changes merged to release branch
3. **Registry Publishing**: Application descriptor published to FAR
4. **Version Management**: Application version incremented
5. **Team Notification**: Release completion notifications

### 3. Platform Release Flow

#### Complete Platform Bundle Generation
*Based on [CI flow [release] - Platform](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887488514/CI+flow+release)*

**Process Components**:

##### Platform Scan Flow
- **Component Monitoring**: Automated scanning for new eureka-component and application versions
- **Version Comparison**: Analysis of current vs. available versions
- **Update Coordination**: Pull request creation for platform updates

##### Platform PR Update Flow
**Trigger**: Platform descriptor changes

**Process**:
1. **Descriptor Retrieval**: Fetch updated platform descriptor and referenced applications
2. **Configuration Updates**: Update `package.json` and related configuration files
3. **Comprehensive Validation**:
   - **Platform Build**: Complete platform compilation
   - **Integration Testing**: End-to-end platform testing
   - **Performance Validation**: Platform performance benchmarks
4. **Status Management**:
   - **Success**: Commit validated changes back to PR
   - **Failure**: Flag PR and alert Release Manager
5. **Notification Pipeline**: Slack notifications to Release Manager and team

##### Platform PR Merge Flow
**Trigger**: Platform PR approval and merge

**Process**:
1. **Final Merge**: Merge approved changes into release branch
2. **Release Tag Creation**: Create official platform release tag
3. **Artifact Generation**: Generate complete platform release bundle
4. **Registry Publishing**: Publish platform artifacts to official repositories
5. **Release Notification**: Announce platform release to all stakeholders

## 📦 Release Artifacts

### Module Artifacts
- **JAR Files**: Maven artifacts in Maven Central
- **Docker Images**: Production containers in Docker Hub
- **NPM Packages**: UI modules in NPM registry
- **Module Descriptors**: API specifications in FOLIO registry

### Application Artifacts
- **Application Descriptors**: Module composition definitions
- **Version Metadata**: Dependency and compatibility information
- **Configuration Templates**: Deployment configuration examples

### Platform Artifacts
*Based on [Artifacts [release]](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/889389109/Artifacts+release)*

**Complete Platform Bundle** (tar.gz archive containing):
- **`platform-descriptor.json`**: Complete platform definition with all component versions
- **Application Descriptors Folder**: All application compositions and dependencies
- **`package.json` & `yarn.lock`**: Frontend dependency management for exact reproducibility
- **`stripes.config.js` & `stripes.modules.js`**: Stripes framework configuration for UI modules

**Platform Bundle Example Structure**:
```
platform-lsp-R2-2025.1.tar.gz
├── platform-descriptor.json
├── applications/
│   ├── app-platform-minimal.json
│   ├── app-acquisitions.json
│   └── [all 31 application descriptors]
├── package.json
├── yarn.lock
├── stripes.config.js
└── stripes.modules.js
```

## 🔍 Validation and Quality Assurance

### Multi-Level Validation
- **Syntax Validation**: JSON structure and schema compliance
- **Dependency Resolution**: Module and application compatibility verification
- **Security Scanning**: Vulnerability assessment and compliance checking
- **Performance Testing**: Load and performance benchmark validation

### Release Criteria
- **All Tests Pass**: 100% test suite success requirement
- **Security Clearance**: No critical security vulnerabilities
- **Documentation Complete**: Release notes and changelog updated
- **Stakeholder Approval**: Required team approvals obtained

## 🚨 Failure Handling and Rollback

### Build Failure Management
- **Immediate Notification**: Release team alerted of failures
- **Detailed Logging**: Comprehensive failure analysis provided
- **Rollback Procedures**: Previous stable version restoration
- **Issue Tracking**: Automatic issue creation for failure analysis

### Release Validation Failures
- **Pre-Release Blocking**: Failed validation prevents release publication
- **Root Cause Analysis**: Detailed failure investigation
- **Team Escalation**: Critical issues escalated to appropriate teams
- **Documentation Updates**: Failure lessons incorporated into process

## 📊 Release Metrics and Monitoring

### Key Performance Indicators
- **Release Success Rate**: Percentage of successful releases
- **Time to Release**: Duration from tag creation to artifact availability
- **Quality Metrics**: Test coverage and defect rates
- **Deployment Readiness**: Time from release to production deployment

### Monitoring and Alerting
- **Real-time Dashboards**: Release pipeline status monitoring
- **Automated Alerts**: Failure and success notifications
- **Trend Analysis**: Release velocity and quality trends
- **Stakeholder Reports**: Regular release status communication

## 🔧 Implementation Status

### Current Implementation
- ✅ **Module Release Flows**: Java and UI module release pipelines operational
- ✅ **Application Publishing**: Automated application descriptor publishing
- ✅ **Platform Bundle Generation**: Complete platform release artifact creation
- ✅ **Registry Integration**: Multi-registry publishing pipeline
- ✅ **Validation Pipeline**: Comprehensive quality assurance processes

### Platform-LSP Release Integration
- ✅ **Automated Scanning**: Continuous monitoring for release-ready components
- ✅ **Bundle Generation**: Complete platform archive creation
- ✅ **Multi-Registry Publishing**: Artifacts published to all required registries
- ✅ **Release Coordination**: Platform release orchestration across all components

## 🔗 Related Documentation

- [Platform Architecture](../../README.md)
- [Eureka CI Flow [Release]](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/887488514/CI+flow+release)
- [Release Artifacts Documentation](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/889389109/Artifacts+release)

---

**Status**: Production Active
**Maintained by**: Kitfox Team DevOps
**Last Updated**: November 2025
