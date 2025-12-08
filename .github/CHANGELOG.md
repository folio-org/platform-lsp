# Changelog

All notable changes to the platform-lsp CI/CD infrastructure will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added - RANCHER-2324: Implement Release CI for platform-lsp

#### New GitHub Actions

- **`build-pr-body`**: Composite action for building pull request body content
- **`calculate-version-increment`**: Composite action for calculating semantic version increments
- **`check-branch-and-pr-status`**: Composite action for validating branch and PR states before operations
- **`fetch-base-file`**: Composite action for fetching base file versions for comparison
- **`fetch-updated-ui-modules`**: Composite action for retrieving updated UI module versions
- **`generate-markdown-reports`**: Composite action for generating markdown-formatted reports
- **`generate-package-diff-report`**: Composite action for generating diff reports between package.json versions
- **`generate-platform-diff-report`**: Composite action for generating collapsed diff and markdown reports comparing platform descriptors between base and head branches
- **`update-applications`**: Composite action for updating application versions by consulting the FOLIO Application Registry (FAR) respecting semver scope rules
- **`update-eureka-components`**: Composite action for resolving newer component versions from GitHub releases when Docker images exist
- **`update-package-json`**: Composite action for updating package.json dependencies
- **`validate-platform`**: Composite action for validating platform descriptor and configuration integrity

#### New Workflows

- **`release-pr-check.yml`**: Workflow for validating pull requests against release branches with comprehensive checks
- **`release-scan.yml`**: Workflow for scanning and detecting available releases that require updates
- **`release-update.yml`**: Workflow entry point for triggering release update processes
- **`release-update-flow.yml`**: Core workflow implementing the release update logic and orchestration

#### Modified Workflows

- **`release-scan.yml`**: Enhanced with proper workflow_call triggers and improved scanning logic
- **`release-pr-check.yml`**: Expanded from minimal stub to full implementation with comprehensive validation
- **`release-update-flow.yml`**: Significantly enhanced from basic implementation to full orchestration with error handling

### Changed

- **Release preparation workflows**: Refactored release preparation orchestrator to use `get-update-config` action and updated workflow version to 1.1
- **Configuration management**: Updated platform-lsp configuration templates with refined dependency and application definitions
- **Documentation**: Enhanced release preparation documentation with improved orchestration logic and result aggregation patterns

### Technical Details

**Commit History:**
- `69395bf`: RANCHER-2324 Implement release CI for platform-lsp (2025-10-30)
- `c06e422`: Update release-scan.yml (2025-10-30)
- `1d0a7e1`: Create release-update.yml (2025-10-30)
- `3fbafab`: Create release-scan.yml (2025-10-30)
- `f23d29c`: Update update-config.yml (2025-10-27)
- `25e6829`: Initialise release-pr-check flow (2025-10-27)

**Key Features:**
- Distributed CI/CD orchestration with matrix strategies
- Team authorization pattern for secure operations
- Semantic versioning scope filtering (major/minor/patch)
- Docker Hub image validation for component updates
- FAR (FOLIO Application Registry) integration for application version resolution
- Comprehensive error handling and GitHub annotations
- Result aggregation and markdown reporting
- Dry-run support for safe workflow validation

**Security:**
- Implements Team Authorization Pattern with GitHub App token generation
- Environment-based fallback with manual approval for unauthorized users
- Fail-closed by default with isolated failure handling

**Best Practices:**
- Single-responsibility jobs and steps
- YAML conventions: 2-space indentation, 120-character line limit
- Bash safety: `set -euo pipefail`, proper quoting and error handling
- Python scripts without classes/annotations for simplicity
- Comprehensive documentation with README files for all actions

---

## [Previous Releases]

_(Previous changelog entries will be added here as needed)_

