# FOLIO Release Artifact Creator

A GitHub Action that automates the creation of complete FOLIO platform release artifacts. This action validates files, collects application descriptors from the FOLIO Application Registry (FAR), packages platform files, and creates a distributable archive with checksums.

## Overview

The FOLIO Release Artifact Creator streamlines the release process by:

1. **Validating** required platform files according to configuration
2. **Collecting** application descriptors from FAR API based on platform-descriptor.json
3. **Packaging** platform files into a staging directory
4. **Creating** a compressed archive with checksums and size validation

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `release_tag` | Release tag to create artifacts for | ✅ | - |
| `github_token` | GitHub token for uploading artifacts | ✅ | - |
| `config_path` | Path to release configuration file | ❌ | `.github/release-package-config.yml` |
| `descriptor_path` | Path to platform descriptor file | ❌ | `platform-descriptor.json` |
| `far_url` | Base URL for FAR API | ❌ | `https://far.ci.folio.org` |

## Outputs

| Output | Description |
|--------|-------------|
| `archive_path` | Path to the created archive |
| `archive_size` | Size of the created archive in bytes |
| `sha256_checksum` | SHA256 checksum of the archive |

## Configuration

### Release Configuration File

Create a `.github/release-package-config.yml` file in your repository with the following structure:

```yaml
# FOLIO Release Configuration
# This file defines the file requirements for FOLIO release artifacts

description: "FOLIO (Eureka) platform release with all files and descriptors"

required_files:
  - "platform-descriptor.json"
  - "application-descriptors/*.json"
  - "package.json"
  - "yarn.lock"
  - "stripes.config.js"
  - "stripes.*.js"

optional_files:
  - "README.md"
  - "LICENSE"
  - "docker/"
  - ".dockerignore"
  - ".npmrc"
  - "tenant-assets/"

# Global settings
settings:
  package_name: "platform-lsp"
  max_archive_size_mb: 500
  archive_format: "tar.gz"

# File patterns to exclude from all variants
exclude_patterns:
  - "ModuleDescriptors/"
  - "node_modules/"
  - "output/"
  - ".git/"
  - ".github/"
  - "*.log"
  - "*.tmp"
  - ".DS_Store"
  - "Thumbs.db"
```

**Configuration Sections:**
- `description`: Human-readable description of the configuration
- `required_files`: Files that must be present for a valid release (supports glob patterns)
- `optional_files`: Files to include if present (supports directories and glob patterns)
- `settings`: Global configuration including package name, size limits, and archive format
- `exclude_patterns`: File patterns to exclude from the final archive

### Platform Descriptor File

Ensure your `platform-descriptor.json` follows the FOLIO platform descriptor format:

```json
{
  "name": "FOLIO LSP",
  "description": "FOLIO LSP (Library Services Platform) is a set of microservices and applications that provide a complete library management system.",
  "version": "R1-2025",
  "eureka-components": [
    {
      "name": "folio-kong",
      "version": "3.9.0"
    },
    {
      "name": "folio-keycloak",
      "version": "26.1.3"
    },
    {
      "name": "folio-module-sidecar",
      "version": "3.0.4"
    }
  ],
  "applications": {
    "required": [
      {
        "name": "app-platform-minimal",
        "version": "2.0.16"
      },
      {
        "name": "app-platform-complete",
        "version": "2.1.31"
      }
    ],
    "optional": [
      {
        "name": "app-erm-usage",
        "version": "2.0.3"
      },
      {
        "name": "app-edge-complete",
        "version": "2.0.6"
      }
    ]
  },
  "dependencies": {
    "postgres": ">=16.0",
    "kafka": ">=3.5.1",
    "opensearch": ">=2.0.0"
  }
}
```

**Structure Overview:**
- `eureka-components`: Core FOLIO infrastructure components (Kong, Keycloak, etc.)
- `applications.required`: Essential applications that must be installed
- `applications.optional`: Additional applications that can be optionally installed
- `dependencies`: External system requirements (databases, message queues, etc.)

## Usage

### Basic Usage

```yaml
name: Create Release Artifacts

on:
  release:
    types: [created]

jobs:
  create-artifacts:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Create release artifacts
        uses: ./.github/actions/folio-release-creator
        with:
          release_tag: ${{ github.event.release.tag_name }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

### Advanced Usage with Custom Configuration

```yaml
name: Create Release Artifacts

on:
  workflow_dispatch:
    inputs:
      release_tag:
        description: 'Release tag'
        required: true
        type: string

jobs:
  create-artifacts:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install yq
        run: |
          sudo wget -O /usr/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
          sudo chmod +x /usr/bin/yq

      - name: Create release artifacts
        id: create-artifacts
        uses: ./.github/actions/folio-release-creator
        with:
          release_tag: ${{ github.event.inputs.release_tag }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          config_path: '.github/custom-release-package-config.yml'
          descriptor_path: 'platform/platform-descriptor.json'
          far_url: 'https://far.folio.org'

      - name: Upload artifact to release
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: ${{ steps.create-artifacts.outputs.archive_path }}
          asset_name: ${{ github.event.inputs.release_tag }}-platform.tar.gz
          asset_content_type: application/gzip

      - name: Display artifact info
        run: |
          echo "Archive created: ${{ steps.create-artifacts.outputs.archive_path }}"
          echo "Archive size: ${{ steps.create-artifacts.outputs.archive_size }} bytes"
          echo "SHA256: ${{ steps.create-artifacts.outputs.sha256_checksum }}"
```

## Components

The action consists of several shell scripts and a Python script that work together:

### 1. File Validation (`validate-files.sh`)
- Validates that all required files exist according to configuration
- Performs additional validation for specific file types (JSON syntax, etc.)
- Reports missing files and validation errors

### 2. Descriptor Collection (`collect_descriptors.py`)
- Fetches application descriptors from FAR API concurrently using ThreadPoolExecutor
- Based on applications listed in platform-descriptor.json (required + optional)
- Saves descriptors to `application-descriptors/` directory with name-version.json format
- Handles API errors gracefully with comprehensive error reporting
- Provides detailed timing and success/failure statistics

### 3. File Collection (`collect-files.sh`)
- Collects platform files according to configuration
- Supports glob patterns and directory structures
- Creates staging directory with organized file structure
- Respects exclusion patterns

### 4. Archive Creation (`create-archive.sh`)
- Creates compressed tar.gz archive from staging directory
- Validates archive size against configuration limits
- Generates SHA256 checksum
- Outputs archive information for subsequent steps

## Requirements

### System Dependencies
- `bash` (with `set -euo pipefail` support)
- `python3` (for FAR API interaction)
- `yq` (for YAML parsing)
- `jq` (for JSON validation)
- `tar` and `gzip` (for archive creation)
- `sha256sum` (for checksum generation)
- `find`, `du`, `cp` (standard Unix utilities)

### GitHub Actions Environment
- Ubuntu 24.04+ recommended
- Python 3.x setup action if not pre-installed
- yq installation (not included in GitHub Actions runners by default)

### Installation Example

```yaml
- name: Install dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y jq
    sudo wget -O /usr/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
    sudo chmod +x /usr/bin/yq

- name: Setup Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.x'
```

## Error Handling

The action provides error handling:

- **Configuration errors**: Missing or invalid configuration files
- **File validation errors**: Missing required files, invalid JSON/YAML
- **API errors**: FAR API connection issues, missing descriptors
- **Size limit errors**: Archive exceeds configured size limits
- **File system errors**: Permission issues, disk space problems

All errors are reported using GitHub Actions error annotations (`::error::`).

## Best Practices

1. **Pin action version**: Use a specific commit SHA or tag when referencing this action
2. **Test configuration**: Validate your release configuration in a test workflow
3. **Monitor archive size**: Set appropriate size limits to prevent excessive artifacts
4. **Secure tokens**: Use repository secrets for GitHub tokens
5. **Validate descriptors**: Ensure platform-descriptor.json is valid before release
6. **Review exclusions**: Regularly update excluded patterns to avoid including sensitive files

## Troubleshooting

### Common Issues

**Missing yq dependency:**
```bash
sudo wget -O /usr/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
sudo chmod +x /usr/bin/yq
```

**FAR API timeout:**
- Check network connectivity to FAR instance
- Verify FAR URL is correct and accessible
- Ensure application versions exist in FAR

**Archive size exceeded:**
- Review and update excluded patterns
- Increase size limit in configuration
- Remove unnecessary files from the repository

**Invalid platform descriptor:**
- Validate JSON syntax
- Ensure all required fields are present
- Check that dependency versions exist in FAR

## Contributing

When modifying this action:

1. Test changes in a fork with sample FOLIO platform repository
2. Ensure backward compatibility with existing configurations
3. Update this README with any new features or breaking changes
4. Follow shell scripting best practices (`set -euo pipefail`, proper quoting)
5. Add appropriate error handling and user-friendly error messages

## License

This action is part of the FOLIO project and follows the same licensing terms.
