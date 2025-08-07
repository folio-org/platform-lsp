# FOLIO Release Artifact Creator

A GitHub Action that automatically packages and uploads complete platform release artifacts when a new GitHub release is created or published.

## Features

- ✅ **Automatic Triggers**: Activates on `release.created`, `release.published`, or manual `workflow_dispatch`
- ✅ **File Validation**: Validates required files and fails gracefully with detailed error messages
- ✅ **FOLIO Integration**: Collects application descriptors from FAR registry
- ✅ **Reproducible Archives**: Creates consistent tar.gz archives with proper naming
- ✅ **Archive Integrity Checks**: SHA256 checksums for all created archives
- ✅ **Configurable**: Supports custom file lists via YAML configuration
- ✅ **Logging**: Detailed progress reporting and error handling

## TBD Features
- ✅ **Slack Notifications**: Notify via Slack when a new release artifact is created (if configured)
- ✅ **Changelog Generation**: Collect and publish changelog based on commit history (if configured)

## Quick Start

### 1. Basic Setup

The action is already configured in this repository. When you create a new release, it will automatically:

1. Validate required files exist
2. Collect platform files and optional components
3. Fetch application descriptors from [FAR registry](https://far.ci.folio.org) API
4. Create tar.gz archive with semantic versioning
5. Upload artifacts to the GitHub release

### 2. Manual Trigger

You can also trigger the action manually:

1. Go to **Actions** → **FOLIO Release Artifact Creator**
2. Click **Run workflow**
3. Enter the release tag (e.g., `R1-2025`, `R1-2025-GA`, `R1-2025-csp-1`)

## Configuration

### Default Configuration

The action uses `.github/release-config.yml` for configuration:

```yaml
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
  - "output/"
```

### Custom Configuration

You can customize the configuration by modifying `.github/release-config.yml`:

**Modify file lists**: Change which files are required or optional

## Archive Naming

Archive are named using the pattern:
- **Name**: `platform-lsp-{version}.tar.gz`

Example:
- `platform-lsp-R1-2025-GA.tar.gz`

## Workflow Details

### Triggers

```yaml
on:
  release:
    types: [created, published]
  workflow_dispatch:
    inputs:
      release_tag:
        description: 'Release tag to create artifacts for'
        required: true
```

### File Validation

The action validates these files before proceeding:

**Required for all variants:**
- `platform-descriptor.json` - FOLIO platform descriptor
- `application-descriptors/*.json` - Application descriptors
- `package.json` - Node.js package definition
- `yarn.lock` - Dependency lock file
- `stripes.config.js` - Stripes configuration file
- `stripes.*.js` - Stripes module descriptors

### Archive Contents
**Complete Variant:**
- Core platform files (platform-descriptor.json, package.json, yarn.lock)
- Application descriptors (application-descriptors/*.json)
- Full Stripes configuration (stripes.config.js, stripes.*.js)
- Documentation (README, LICENSE)
- Docker configuration
- Tenant assets

## Troubleshooting

### Common Issues

1. **Missing Required Files**
   ```
   Error: Required file 'platform-descriptor.json' not found
   ```
   **Solution**: Ensure all required files are present in the repository root.

2. **MGR Applications API Failure**
   ```
   Error: Failed to fetch applications from FAR API
   ```
   **Solution**: Check the `far_url` configuration and ensure the FAR API is accessible.

3. **Archive Too Large**
   ```
   Error: Archive size exceeds limit (500MB)
   ```
   **Solution**: Adjust `max_archive_size_mb` in configuration or exclude large directories.

### Debug Mode

Enable debug logging by setting repository variable:
```
ACTIONS_STEP_DEBUG = true
```

### Manual Validation

Test file validation locally:
```bash
# Validate files for complete variant
./.github/actions/folio-release-creator/validate-files.sh
```

## API Integration

### MGR Applications

Workflow automatically fetches application descriptors from:
- Base URL: `https://far.ci.folio.org`
- Endpoint: `/applications`
- Format: JSON application descriptors

This can be customized via the `far_url` input parameter.

## Security

- ✅ Uses minimal required permissions (`contents: write`, `actions: read`)
- ✅ No secrets stored in logs or artifacts
- ✅ Reproducible builds with deterministic timestamps
- ✅ SHA256 checksums for all archives
- ✅ Validation of archive integrity

## Performance

- **Execution Time**: < 5 minutes for standard repositories
- **Archive Size**: Configurable limits (default: 500MB)
- **Efficient Collection**: Smart file pattern matching and exclusions

## Contributing

To modify or extend this action:

1. **Update Configuration**: Modify `.github/release-config.yml`
2. **Extend Scripts**: Edit files in `.github/actions/folio-release-creator/`
3. **Test Changes**: Use workflow_dispatch to test with existing releases
4. **Validate**: Ensure all required files are detected and archived correctly

## Support

For issues or questions:
1. Check the [Actions logs] for detailed error messages
2. Review the configuration file for variant requirements
3. Test with workflow_dispatch using a known good release tag
4. Open an issue with the specific error message and repository context
