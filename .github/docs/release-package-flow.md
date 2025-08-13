# FOLIO Platform Release Package Workflow

This workflow (`release-package.yml`) automates the process of validating, packaging, and uploading FOLIO platform release artifacts to GitHub Releases.

## Overview

The workflow is triggered by:
- **Release events** (when a release is created)
- **Manual dispatch** (workflow_dispatch with inputs):
  - `release_tag` (required): Release tag to create artifacts for
  - `far_url` (optional): FAR API base URL (default: https://far.ci.folio.org)

It uses the custom `folio-release-creator` action to handle the complete release artifact creation process and includes Slack notifications for status updates.

## Main Jobs

### 1. validate-and-prepare
- **Purpose**: Early validation and setup
- **Timeout**: 1 minute
- **Steps**:
  - Checkout repository
  - Validate configuration file exists (`.github/release-package-config.yml`)
  - Validate release tag is provided
  - Set up environment variables

### 2. create-release-artifact
- **Purpose**: Create and upload the complete release artifact
- **Timeout**: 5 minutes
- **Dependencies**: Requires `validate-and-prepare` to complete successfully
- **Permissions**: `contents: write`, `actions: read`
- **Steps**:
  1. **Checkout repository**
  2. **Cache dependencies** (yq, Python packages)
  3. **Create release artifact** using `folio-release-creator` action:
     - Install system dependencies (python3, jq, yq, tar)
     - Validate required files according to configuration
     - Collect application descriptors from FAR API
     - Collect and organize platform files
     - Create compressed tar.gz archive with manifest
     - Generate SHA256 checksum
  4. **Upload and verify release artifacts**:
     - Create SHA256 checksum file
     - Upload the main archive file and checksum to GitHub Release
     - Verify successful upload by checking release assets
  5. **Post workflow summary** to GitHub Actions
  6. **Send Slack notification** (success/failure status)

## Configuration

The workflow uses several environment variables:
- `FAR_URL`: FAR API base URL (default: https://far.ci.folio.org)
- `CONFIG_PATH`: Release configuration file (`.github/release-package-config.yml`)
- `DESCRIPTOR_PATH`: Platform descriptor file (`platform-descriptor.json`)
- `SLACK_NOTIFICATION_CHANNEL`: Slack channel for notifications (default: `#folio-rancher-debug-notifications`)
- `RELEASE_TAG`: The release tag being processed
- `GITHUB_TOKEN`: GitHub token used across multiple steps

## Features

- **Concurrency control**: Prevents multiple releases for the same ref (group: `release-${{ github.ref }}`, no cancellation)
- **Dependency caching**: Caches yq binary and Python packages for faster subsequent runs
- **Error handling**: Comprehensive validation and error reporting
- **Artifact verification**: Confirms successful upload to GitHub Release
- **Slack integration**: Automated notifications with rich formatting
- **Summary reporting**: Detailed workflow summaries in GitHub Actions UI

## Architecture Diagram
See the detailed workflow and script logic in the diagram below:

[![Workflow Diagram](./release-package-flow.svg)](./release-package-flow.svg)

You can render or download the SVG file, or view/edit the source in `flow.mmd` with any MermaidJS-compatible tool or VSCode extension.

---

For more details on the release process and configuration, see the main repository documentation and `.github/release-package-config.yml`.