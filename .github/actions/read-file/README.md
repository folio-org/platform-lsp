# Read File Action

Universal file reader supporting multiple sources: working tree, branches, commits, and tags with optional JSON validation and content output. This action provides a flexible way to read files from different locations in your repository's history or current state.

## Purpose

This action provides a unified interface for reading files from various sources in your Git repository:
- **Working Tree**: Read files from the current checkout
- **Branches**: Read files from any branch (local or remote)
- **Commits**: Read files from specific commit SHAs
- **Tags**: Read files from tagged versions

Features:
- Configurable error handling (fail vs warn on missing files)
- Optional JSON validation using `jq`
- Optional file content output for further processing
- Flexible output filename or in-memory reading
- Source information tracking

## Usage

### Read from Working Tree (Current Files)

```yaml
- name: Read current descriptor
  id: read-descriptor
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: platform-descriptor.json
    source: worktree
    validate_json: true
```

### Read from a Branch

```yaml
- name: Read file from base branch
  id: read-base
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: platform-descriptor.json
    source: branch
    ref: R1-2025
    output_filename: descriptor.base.json
    validate_json: true
```

### Read from a Commit

```yaml
- name: Read file from specific commit
  id: read-commit
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: package.json
    source: commit
    ref: abc123def456
    validate_json: true
    output_content: true
```

### Read from a Tag

```yaml
- name: Read file from release tag
  id: read-tag
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: VERSION
    source: tag
    ref: v1.0.0
    validate_json: false
    output_content: true
```

### Read Content Only (No File Output)

```yaml
- name: Read JSON content for processing
  id: read-json
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: config.json
    source: branch
    ref: production
    validate_json: true
    output_content: true
    # No output_filename = content only in outputs

- name: Process JSON content
  run: |
    echo '${{ steps.read-json.outputs.file_content }}' | jq '.version'
```

### Graceful Handling with Warning on Missing

```yaml
- name: Try to read optional config
  id: read-config
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: optional-config.json
    source: worktree
    fail_on_missing: false
    output_content: true

- name: Use config if available
  if: steps.read-config.outputs.file_exists == 'true'
  run: |
    echo "Config found: ${{ steps.read-config.outputs.file_content }}"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `file_path` | Path to file in repository (e.g., `platform-descriptor.json`) | **Yes** | - |
| `source` | Source to read from: `worktree`, `branch`, `commit`, or `tag` | No | `worktree` |
| `ref` | Git reference (branch name, commit SHA, or tag) when source is not `worktree` | Conditional* | `''` |
| `output_filename` | Output filename. If empty, content is only available via outputs | No | `''` |
| `validate_json` | Whether to validate file as JSON using `jq` | No | `false` |
| `fail_on_missing` | Whether to fail workflow if file is missing or invalid | No | `true` |
| `output_content` | Whether to output file content as output variable | No | `true` |

\* `ref` is required when `source` is `branch`, `commit`, or `tag`

## Outputs

| Output | Description | Example |
|--------|-------------|---------|
| `file_path` | Path to output file (if `output_filename` specified) | `descriptor.base.json` |
| `file_exists` | Whether file was successfully read (`true` or `false`) | `true` |
| `file_content` | File content (if `output_content=true`) | `{"version": "1.0"}` |
| `source_info` | Information about the source | `branch:R1-2025 (abc123...)` |

## Source Types

### `worktree`
Reads files from the current working tree (checked-out files).
- No `ref` required
- Files must exist in current checkout
- Fastest option, no git operations needed

### `branch`
Reads files from a branch (local or remote).
- Requires `ref` with branch name
- Automatically fetches latest from `origin/<branch>`
- Falls back to local refs if fetch fails
- Use for comparing with base branches

### `commit`
Reads files from a specific commit SHA.
- Requires `ref` with full or short commit SHA
- No fetch performed (commit must be in local history)
- Use for specific point-in-time comparisons

### `tag`
Reads files from a tagged version.
- Requires `ref` with tag name
- No fetch performed (tag must be in local history)
- Use for release comparisons

## Behavior

### Success Path

1. Validates source type and required inputs
2. Determines output destination (file or temp)
3. Reads file based on source:
   - **worktree**: Copies from working tree
   - **branch/commit/tag**: Uses `git show` to extract content
4. Validates file is not empty
5. Optionally validates JSON structure
6. Outputs file path, existence status, and content
7. Provides source information for traceability

### Error Handling

#### When `fail_on_missing=true` (default)
- Missing files cause workflow failure with error annotation
- Invalid JSON (if validation enabled) causes failure
- Empty files cause failure
- Missing required inputs cause failure

#### When `fail_on_missing=false`
- Missing files produce warning annotations
- Outputs `file_exists=false`
- Other outputs are empty
- Workflow continues

## Common Patterns

### Compare Current with Base Branch

```yaml
- name: Read current descriptor
  id: current
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: platform-descriptor.json
    source: worktree
    validate_json: true
    output_content: true

- name: Read base descriptor
  id: base
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: platform-descriptor.json
    source: branch
    ref: ${{ github.base_ref }}
    validate_json: true
    output_content: true

- name: Compare versions
  run: |
    current_version=$(echo '${{ steps.current.outputs.file_content }}' | jq -r '.version')
    base_version=$(echo '${{ steps.base.outputs.file_content }}' | jq -r '.version')
    echo "Current: $current_version, Base: $base_version"
```

### Read Multiple Files from Same Source

```yaml
- name: Read package.json from release
  id: pkg
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: package.json
    source: tag
    ref: v1.0.0
    validate_json: true
    output_content: true

- name: Read descriptor from same release
  id: desc
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: platform-descriptor.json
    source: tag
    ref: v1.0.0
    validate_json: true
    output_content: true
```

### Conditional File Processing

```yaml
- name: Try to read config
  id: config
  uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: .custom-config.json
    source: worktree
    validate_json: true
    fail_on_missing: false
    output_content: true

- name: Use defaults if config missing
  run: |
    if [ "${{ steps.config.outputs.file_exists }}" = "true" ]; then
      echo "Using custom config"
      echo '${{ steps.config.outputs.file_content }}' > config.json
    else
      echo "Using defaults"
      echo '{"default": true}' > config.json
    fi
```

## Migration from fetch-base-file

If you're migrating from the previous `fetch-base-file` action:

**Old usage:**
```yaml
- uses: folio-org/platform-lsp/.github/actions/fetch-base-file@master
  with:
    base_branch: R1-2025
    file_path: platform-descriptor.json
    validate_json: true
```

**New equivalent:**
```yaml
- uses: folio-org/platform-lsp/.github/actions/read-file@master
  with:
    file_path: platform-descriptor.json
    source: branch
    ref: R1-2025
    validate_json: true
```

**Key changes:**
- `base_branch` → `ref` (with `source: branch`)
- `validate_json` default changed from `true` to `false` (be explicit)
- `output_content` default changed from `false` to `true`

## Requirements

- Git repository (except for `source: worktree`)
- `jq` installed (only if `validate_json: true`)
- Proper checkout (use `actions/checkout` first)

## Security Considerations

- Uses `git show` for historical file access (read-only operation)
- No modifications to repository state
- Validates inputs to prevent injection
- Handles errors gracefully with clear messaging
- Uses temporary files with cleanup when needed

## Performance

- **worktree**: Fastest, direct file copy
- **branch**: Includes fetch operation (~1-2s overhead)
- **commit/tag**: No fetch, uses local history
- Large files may impact action duration

## Troubleshooting

### "Not in a git repository"
Ensure `actions/checkout` is run before this action.

### "Failed to read file from branch"
- Branch may not exist on remote
- File may not exist in that branch
- Network issues with fetch

### "File is not valid JSON"
- Set `validate_json: false` if file is not JSON
- Check file encoding and format
- Review file content in error output

### "ref input is required"
When using `source: branch|commit|tag`, you must provide `ref`.

## Examples Repository

For more examples, see the workflow files in the repository that use this action.

## License

This action is part of the FOLIO platform and follows the same license terms.


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

