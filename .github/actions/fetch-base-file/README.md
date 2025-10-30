# Fetch Base File Action

Fetches and validates a file from a base branch using `git show`. This action enables comparing current state with a baseline by retrieving files from a reference branch without checking it out.

## Purpose

This action solves the common pattern of needing to fetch a file from a base branch for comparison or diff generation. It provides:
- Safe file retrieval using `git show`
- Configurable error handling (fail vs warn)
- Optional JSON validation
- Optional content output for further processing

## Usage

### Basic Usage

Fetch a file from a base branch with error on missing:

```yaml
- name: Fetch base descriptor
  id: fetch-descriptor
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@master
  with:
    base_branch: R1-2025
    file_path: platform-descriptor.json
```

### Advanced Usage with Content Output

Fetch a file with warning on missing and output content:

```yaml
- name: Fetch base package.json
  id: fetch-package
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@master
  with:
    base_branch: R1-2025
    file_path: package.json
    output_filename: package.json.base
    validate_json: true
    fail_on_missing: false
    output_content: true

- name: Use fetched file
  if: steps.fetch-package.outputs.file_exists == 'true'
  run: |
    echo "File path: ${{ steps.fetch-package.outputs.file_path }}"
    echo "Content: ${{ steps.fetch-package.outputs.file_content }}"
```

### Non-JSON File

Fetch a non-JSON file without validation:

```yaml
- name: Fetch base README
  id: fetch-readme
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@master
  with:
    base_branch: main
    file_path: README.md
    validate_json: false
    fail_on_missing: false
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `base_branch` | Base branch to fetch file from (e.g., `R1-2025`, `main`) | Yes | - |
| `file_path` | Path to file in repository (e.g., `platform-descriptor.json`) | Yes | - |
| `output_filename` | Name for the fetched file. If not specified, uses pattern `<name>.base.<ext>` | No | auto-generated |
| `validate_json` | Whether to validate file as JSON using `jq` | No | `true` |
| `fail_on_missing` | Whether to fail workflow if file is missing or invalid | No | `true` |
| `output_content` | Whether to output file content as `file_content` output variable | No | `false` |

## Outputs

| Output | Description | Example |
|--------|-------------|---------|
| `file_path` | Path to the fetched base file | `platform-descriptor.base.json` |
| `file_exists` | Whether file was successfully fetched (`true` or `false`) | `true` |
| `file_content` | File content (only if `output_content=true`) | `{"version": "1.0"}` |

## Behavior

### Success Path

1. Determines output filename (custom or auto-generated)
2. Fetches latest base branch metadata with `git fetch`
3. Uses `git show origin/<base_branch>:<file_path>` to extract file
4. Validates file is not empty
5. Optionally validates JSON structure with `jq`
6. Optionally outputs file content
7. Returns file path and success status

### Error Handling

#### When `fail_on_missing=true` (default)

- Missing file → `::error::`, workflow fails
- Empty file → `::error::`, workflow fails  
- Invalid JSON (if `validate_json=true`) → `::error::`, workflow fails

#### When `fail_on_missing=false`

- Missing file → `::warning::`, `file_exists=false`, continue
- Empty file → `::warning::`, `file_exists=false`, continue
- Invalid JSON (if `validate_json=true`) → `::warning::`, `file_exists=false`, continue

### Output Filename Pattern

If `output_filename` is not provided:
- `platform-descriptor.json` → `platform-descriptor.base.json`
- `package.json` → `package.base.json`
- `README.md` → `README.base.md`
- `config` (no extension) → `config.base`

## Requirements

- Git repository must be checked out with `actions/checkout@v4`
- Repository must have been fetched with `fetch-depth: 0` or base branch must exist in remote
- `jq` is required if `validate_json=true` (pre-installed in GitHub-hosted runners)

## Examples

### Example 1: Fetch Required Platform Descriptor

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0

- name: Fetch base platform descriptor
  id: fetch-base
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@master
  with:
    base_branch: ${{ inputs.release_branch }}
    file_path: platform-descriptor.json
    validate_json: true
    fail_on_missing: true

- name: Compare with current
  run: |
    diff "${{ steps.fetch-base.outputs.file_path }}" platform-descriptor.json || true
```

### Example 2: Fetch Optional Package JSON

```yaml
- name: Fetch base package.json
  id: fetch-package
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@master
  with:
    base_branch: ${{ inputs.release_branch }}
    file_path: package.json
    validate_json: true
    fail_on_missing: false
    output_content: true

- name: Process if exists
  if: steps.fetch-package.outputs.file_exists == 'true'
  run: |
    echo "Base package.json version:"
    echo '${{ steps.fetch-package.outputs.file_content }}' | jq -r '.version'
```

### Example 3: Fetch Multiple Files

```yaml
- name: Fetch base descriptor
  id: fetch-descriptor
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@master
  with:
    base_branch: R1-2025
    file_path: platform-descriptor.json

- name: Fetch base package
  id: fetch-package
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@master
  with:
    base_branch: R1-2025
    file_path: package.json
    fail_on_missing: false

- name: Generate diff report
  run: |
    echo "Files fetched:"
    echo "- ${{ steps.fetch-descriptor.outputs.file_path }}"
    [ "${{ steps.fetch-package.outputs.file_exists }}" = "true" ] && \
      echo "- ${{ steps.fetch-package.outputs.file_path }}"
```

## Implementation Details

### Safe Shell Practices

The action follows FOLIO safe shell standards:
- `set -euo pipefail` for strict error handling
- `IFS=$'\n\t'` to prevent word splitting issues
- All variables properly quoted
- Explicit error checking before operations

### Git Operations

- Uses `git fetch origin "$BASE_BRANCH" --depth=1` to minimize data transfer
- Uses `git show "origin/$BASE_BRANCH:$FILE_PATH"` to extract file without checkout
- Handles missing branches/files gracefully based on `fail_on_missing` setting

### JSON Validation

When `validate_json=true`:
- Uses `jq empty "$file"` to validate JSON structure
- Compacts JSON with `jq -c .` when outputting content
- Preserves exact content when `validate_json=false`

## Troubleshooting

### Error: "Failed to fetch file from base branch"

**Causes:**
- Base branch doesn't exist in remote
- File doesn't exist in base branch
- Insufficient git fetch depth

**Solutions:**
- Verify base branch name is correct
- Ensure repository is checked out with `fetch-depth: 0`
- Set `fail_on_missing: false` if file is optional

### Error: "File is not valid JSON"

**Causes:**
- File contains invalid JSON syntax
- File is corrupted

**Solutions:**
- Check file syntax in base branch
- Set `validate_json: false` if file is not JSON
- Set `fail_on_missing: false` to continue on validation errors

### Warning: "File is empty"

**Causes:**
- File exists but has no content in base branch

**Solutions:**
- Check base branch file content
- Set `fail_on_missing: false` to treat as non-error

## Related Actions

- [check-branch-and-pr-status](../check-branch-and-pr-status/) - Check branch existence and PR status
- [generate-platform-diff-report](../generate-platform-diff-report/) - Generate diff reports (uses this action)

## Maintenance

### Adding Support for New Validation Types

To add validation beyond JSON:

1. Add new input (e.g., `validate_yaml`)
2. Add validation logic in script
3. Update documentation
4. Add test cases

### Extending Output Options

To add new output formats:

1. Add new input (e.g., `output_format`)
2. Add format handling in content output section
3. Update outputs documentation
4. Add examples

---

**Author:** FOLIO DevOps  
**License:** Apache 2.0  
**Support:** Create an issue in the platform-lsp repository

