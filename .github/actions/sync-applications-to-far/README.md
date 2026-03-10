# Sync Applications to FAR

Synchronize application descriptors from folio-org GitHub repositories to FOLIO Application Registry (FAR).

## Description

This action automates the process of keeping FAR up-to-date with application releases published on GitHub. It reads the applications listed in `platform-descriptor.json`, compares GitHub releases with FAR versions, downloads missing `application-descriptor.json` files from GitHub release assets, and POSTs them to FAR.

### Key Features

- **Automatic Discovery**: Reads applications from platform descriptor
- **Version Comparison**: Compares GitHub releases with FAR versions to identify gaps
- **Batch Processing**: Processes multiple applications concurrently for efficiency
- **Dry Run Mode**: Preview what would be synced without modifying FAR
- **Error Resilience**: Continues processing all applications even if some fail
- **Detailed Reporting**: Provides comprehensive sync results with error details

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `descriptor-path` | Path to platform descriptor file | No | `platform-descriptor.json` |
| `far-base-url` | FAR base URL | No | `https://far.ci.folio.org` |
| `github-token` | GitHub token for repository access | Yes | - |
| `dry-run` | Preview mode without POSTing to FAR (true\|false) | No | `false` |
| `application-groups` | Comma-separated list of application groups to process | No | `required,optional` |
| `request-timeout` | HTTP request timeout (seconds) | No | `10.0` |
| `max-retries` | Maximum number of HTTP request retries | No | `3` |
| `retry-backoff` | Base backoff time in seconds for retries | No | `1.0` |
| `log-level` | Level of logging verbosity (INFO, DEBUG, WARNING, ERROR) | No | `INFO` |
| `far-auth-token` | FAR API authentication token (optional) | No | `''` |

## Outputs

| Output | Description |
|--------|-------------|
| `synced-count` | Number of descriptors successfully synced to FAR |
| `failed-count` | Number of failed sync attempts |
| `skipped-count` | Number of descriptors skipped (already in FAR) |
| `summary` | JSON summary of results with detailed breakdown |

## Usage

### Basic Example

```yaml
- name: Sync applications to FAR
  id: sync
  uses: folio-org/platform-lsp/.github/actions/sync-applications-to-far@master
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Dry Run Mode

Preview what would be synced without modifying FAR:

```yaml
- name: Preview sync to FAR
  uses: folio-org/platform-lsp/.github/actions/sync-applications-to-far@master
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    dry-run: 'true'
    log-level: 'DEBUG'
```

### Custom Groups

Process only specific application groups:

```yaml
- name: Sync required apps to FAR
  uses: folio-org/platform-lsp/.github/actions/sync-applications-to-far@master
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    application-groups: 'required'
```

### With FAR Authentication

If FAR requires authentication:

```yaml
- name: Sync to authenticated FAR
  uses: folio-org/platform-lsp/.github/actions/sync-applications-to-far@master
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    far-auth-token: ${{ secrets.FAR_AUTH_TOKEN }}
```

### Complete Workflow Example

```yaml
name: Sync Applications to FAR

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:
    inputs:
      dry_run:
        description: 'Dry run mode'
        type: boolean
        default: false

jobs:
  sync-to-far:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Sync applications to FAR
        id: sync
        uses: folio-org/platform-lsp/.github/actions/sync-applications-to-far@master
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          dry-run: ${{ inputs.dry_run && 'true' || 'false' }}
          log-level: 'INFO'
      
      - name: Report results
        if: always()
        run: |
          echo "Synced: ${{ steps.sync.outputs.synced-count }}"
          echo "Skipped: ${{ steps.sync.outputs.skipped-count }}"
          echo "Failed: ${{ steps.sync.outputs.failed-count }}"
      
      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            const summary = JSON.parse('${{ steps.sync.outputs.summary }}');
            console.error('Sync failed:', summary.errors);
```

## How It Works

1. **Load Platform Descriptor**: Reads `platform-descriptor.json` to get list of applications
2. **Collect Applications**: Extracts applications from specified groups (`required`, `optional`, etc.)
3. **Fetch GitHub Releases**: For each application, fetches release tags from `folio-org/{app-name}` repository
4. **Normalize Versions**: Strips `v` prefix from tags (e.g., `v2.0.51` → `2.0.51`)
5. **Fetch FAR Versions**: Queries FAR API to get existing versions for each application
6. **Compare Versions**: Identifies versions present in GitHub but missing from FAR
7. **Download Descriptors**: Downloads `application-descriptor.json` from GitHub release assets
8. **POST to FAR**: Submits descriptors to FAR via `POST /applications` endpoint
9. **Report Results**: Provides detailed summary of synced, skipped, and failed descriptors

## Error Handling

The action follows a "continue on error" strategy:

- **Repository Not Found**: Logs warning and continues
- **Release Asset Missing**: Logs warning and skips that version
- **FAR 409 Conflict**: Logs as skipped (already exists)
- **FAR 4xx/5xx Errors**: Logs error and continues with next version
- **Network Failures**: Retries with exponential backoff up to `max-retries` times

All errors are collected and reported in the final summary without stopping the entire sync process.

## Requirements

### GitHub Token Permissions

The action requires a GitHub token with the following permissions:
- `contents: read` - To access repository releases and download assets

For public repositories, the default `${{ secrets.GITHUB_TOKEN }}` is sufficient.

### Platform Descriptor Format

The `platform-descriptor.json` must contain an `applications` object with one or more groups:

```json
{
  "applications": {
    "required": [
      {"name": "app-platform-minimal", "version": "2.0.24"},
      {"name": "app-platform-complete", "version": "2.1.40"}
    ],
    "optional": [
      {"name": "app-acquisitions", "version": "1.0.22"}
    ]
  }
}
```

### GitHub Release Assets

Each application release must include an `application-descriptor.json` asset for the sync to succeed. Releases without this asset will be skipped with a warning.

## Performance

- **Concurrent Processing**: Uses thread pool to process multiple applications simultaneously
- **Caching**: FAR version queries are cached to avoid redundant API calls
- **Rate Limiting**: Automatically handles GitHub and FAR API rate limits with retry logic
- **Typical Performance**: Processes ~15 applications in 30-60 seconds

## Troubleshooting

### No versions synced

**Possible causes:**
- All versions already exist in FAR (check `skipped-count`)
- Repository doesn't exist in folio-org
- Releases don't have `application-descriptor.json` assets

**Solution:** Run with `dry-run: 'true'` and `log-level: 'DEBUG'` to see detailed information.

### GitHub API rate limit errors

**Cause:** Too many API requests in short time

**Solution:**
- Use authenticated token (increases rate limit)
- Reduce `max-workers` in script (requires code modification)
- Add delay between workflow runs

### FAR authentication errors

**Cause:** FAR endpoint requires authentication but token not provided

**Solution:** Add `far-auth-token` input with valid FAR API token

### Descriptor format errors

**Cause:** Downloaded descriptor doesn't match FAR's expected schema

**Solution:** Verify application-descriptor.json format in GitHub releases matches FAR requirements

## Related Actions

- **[update-applications](../update-applications/)**: Updates application versions in platform descriptor from FAR
- **[folio-release-creator](../folio-release-creator/)**: Collects descriptors from FAR for release packaging

## Development

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GITHUB_TOKEN="ghp_your_token_here"
export DESCRIPTOR_PATH="platform-descriptor.json"
export DRY_RUN="true"
export LOG_LEVEL="DEBUG"

# Run script
python sync-applications-to-far.py
```

### Debugging

Enable debug logging to see detailed information:

```yaml
with:
  log-level: 'DEBUG'
```

This shows:
- Exact API URLs being called
- Version lists from GitHub and FAR
- HTTP request/response details
- Descriptor content in dry-run mode

## License

See the [LICENSE](../../../../LICENSE) file in the repository root.

## Support

For issues or questions:
- Open an issue in the [platform-lsp repository](https://github.com/folio-org/platform-lsp/issues)
- Check existing workflows for usage examples
- Review action logs for error details
