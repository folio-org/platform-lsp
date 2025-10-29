# Action Extraction Report #2: fetch-base-file

**Phase:** 1 (High Priority)  
**Complexity Reduction:** ~80 lines (pattern appears twice)  
**Impact:** High  
**Implementation Time:** 2-3 hours

---

## Overview

### Purpose
Fetches and validates a file from a base branch in a Git repository. This is a common pattern needed when comparing current state with a baseline for diff generation or update detection.

### Current Problem
The pattern appears **twice** in the workflow with nearly identical code (~40 lines each):
1. Fetching `platform-descriptor.json` from the base branch
2. Fetching `package.json` from the base branch

This violates the DRY (Don't Repeat Yourself) principle and makes maintenance harder.

### Benefits of Extraction
- **DRY Compliance:** Eliminates 80 lines of duplicated code
- **Reusability:** Can fetch any file from any base branch
- **Consistency:** Single implementation ensures uniform behavior
- **Maintainability:** Fix bugs once, benefit everywhere

---

## Current Implementation

### Location in Workflow

**Instance 1:** `.github/workflows/release-update-flow.yml`  
**Job:** `update-platform-descriptor`  
**Step:** "Fetch and save base branch descriptor"

**Instance 2:** `.github/workflows/release-update-flow.yml`  
**Job:** `update-package-json`  
**Step:** "Fetch base branch package.json"

### Current Code - Instance 1 (Platform Descriptor)

```yaml
- name: 'Fetch and save base branch descriptor'
  id: fetch-base-descriptor
  env:
    RELEASE_BRANCH: ${{ inputs.release_branch }}
    STATE_FILE: ${{ env.STATE_FILE }}
  run: |
    set -euo pipefail
    IFS=$'\n\t'
    echo "::notice::Fetching base descriptor from release branch: $RELEASE_BRANCH"
    git fetch origin "$RELEASE_BRANCH" --depth=1
    BASE_STATE_FILE="platform-descriptor.base.json"
    if ! git show "origin/$RELEASE_BRANCH:$STATE_FILE" > "$BASE_STATE_FILE" 2>/dev/null; then
      echo "::error::Failed to fetch $STATE_FILE from base branch $RELEASE_BRANCH"
      exit 1
    fi
    if [ ! -s "$BASE_STATE_FILE" ]; then
      echo "::error::Base descriptor file is empty"
      exit 1
    fi
    if ! jq empty "$BASE_STATE_FILE" 2>/dev/null; then
      echo "::error::Base descriptor is not valid JSON"
      cat "$BASE_STATE_FILE"
      exit 1
    fi
    echo "base_state_file=$BASE_STATE_FILE" >> "$GITHUB_OUTPUT"
    echo "::notice::Base descriptor saved to $BASE_STATE_FILE"
```

### Current Code - Instance 2 (Package JSON)

```yaml
- name: 'Fetch base branch package.json'
  id: fetch-base-package-json
  env:
    RELEASE_BRANCH: ${{ inputs.release_branch }}
  run: |
    set -euo pipefail
    IFS=$'\n\t'
    echo "::notice::Fetching base package.json from release branch: $RELEASE_BRANCH"
    BASE_PACKAGE_JSON="package.json.base"
    if ! git show "origin/$RELEASE_BRANCH:package.json" > "$BASE_PACKAGE_JSON" 2>/dev/null; then
      echo "::warning::Failed to fetch package.json from base branch $RELEASE_BRANCH"
      echo "base_package_json_exists=false" >> "$GITHUB_OUTPUT"
      exit 0
    fi
    if [ ! -s "$BASE_PACKAGE_JSON" ]; then
      echo "::warning::Base package.json file is empty"
      echo "base_package_json_exists=false" >> "$GITHUB_OUTPUT"
      exit 0
    fi
    if ! jq empty "$BASE_PACKAGE_JSON" 2>/dev/null; then
      echo "::warning::Base package.json is not valid JSON"
      echo "base_package_json_exists=false" >> "$GITHUB_OUTPUT"
      exit 0
    fi
    BASE_PACKAGE_JSON_CONTENT=$(jq -c . "$BASE_PACKAGE_JSON")
    {
      echo 'base_package_json_content<<EOF'
      echo "$BASE_PACKAGE_JSON_CONTENT"
      echo 'EOF'
    } >> "$GITHUB_OUTPUT"
    echo "base_package_json_file=$BASE_PACKAGE_JSON" >> "$GITHUB_OUTPUT"
    echo "base_package_json_exists=true" >> "$GITHUB_OUTPUT"
    echo "::notice::Base package.json saved to $BASE_PACKAGE_JSON"
```

### Complexity Analysis
- **Total lines of code:** ~80 lines across 2 instances
- **Duplication:** 90% code similarity
- **Dependencies:** `git`, `jq`
- **Variations:** Error vs warning handling, content output
- **Consolidation opportunity:** High

---

## Action Specification

### Action Metadata

```yaml
name: 'Fetch Base File'
description: 'Fetches and validates a file from a base branch using git show'
author: 'FOLIO DevOps'

branding:
  icon: 'download'
  color: 'green'
```

### Inputs

```yaml
inputs:
  base_branch:
    description: 'Base branch to fetch file from'
    required: true
    type: string
  
  file_path:
    description: 'Path to file in repository (e.g., platform-descriptor.json)'
    required: true
    type: string
  
  output_filename:
    description: 'Name for the fetched file (default: <original>.base)'
    required: false
    type: string
  
  validate_json:
    description: 'Whether to validate file as JSON'
    required: false
    default: 'true'
    type: boolean
  
  fail_on_missing:
    description: 'Whether to fail if file is missing (false = warning only)'
    required: false
    default: 'true'
    type: boolean
  
  output_content:
    description: 'Whether to output file content as output variable'
    required: false
    default: 'false'
    type: boolean
```

### Outputs

```yaml
outputs:
  file_path:
    description: 'Path to the fetched base file'
    value: ${{ steps.fetch.outputs.file_path }}
  
  file_exists:
    description: 'Whether the file was successfully fetched (true/false)'
    value: ${{ steps.fetch.outputs.file_exists }}
  
  file_content:
    description: 'File content (if output_content=true and file is JSON)'
    value: ${{ steps.fetch.outputs.file_content }}
```

---

## Implementation Guide

### Step 1: Create Action Directory

```bash
mkdir -p .github/actions/fetch-base-file
cd .github/actions/fetch-base-file
```

### Step 2: Create `action.yml`

```yaml
name: 'Fetch Base File'
description: 'Fetches and validates a file from a base branch using git show'
author: 'FOLIO DevOps'

inputs:
  base_branch:
    description: 'Base branch to fetch file from'
    required: true
  file_path:
    description: 'Path to file in repository'
    required: true
  output_filename:
    description: 'Name for the fetched file'
    required: false
  validate_json:
    description: 'Whether to validate file as JSON'
    required: false
    default: 'true'
  fail_on_missing:
    description: 'Whether to fail if file is missing'
    required: false
    default: 'true'
  output_content:
    description: 'Whether to output file content'
    required: false
    default: 'false'

outputs:
  file_path:
    description: 'Path to the fetched base file'
    value: ${{ steps.fetch.outputs.file_path }}
  file_exists:
    description: 'Whether the file was successfully fetched'
    value: ${{ steps.fetch.outputs.file_exists }}
  file_content:
    description: 'File content if requested'
    value: ${{ steps.fetch.outputs.file_content }}

runs:
  using: 'composite'
  steps:
    - name: 'Fetch file from base branch'
      id: fetch
      shell: bash
      env:
        BASE_BRANCH: ${{ inputs.base_branch }}
        FILE_PATH: ${{ inputs.file_path }}
        OUTPUT_FILENAME: ${{ inputs.output_filename }}
        VALIDATE_JSON: ${{ inputs.validate_json }}
        FAIL_ON_MISSING: ${{ inputs.fail_on_missing }}
        OUTPUT_CONTENT: ${{ inputs.output_content }}
      run: |
        set -euo pipefail
        IFS=$'\n\t'
        
        # Determine output filename
        if [ -n "${OUTPUT_FILENAME}" ]; then
          base_file="$OUTPUT_FILENAME"
        else
          filename=$(basename "$FILE_PATH")
          base_file="${filename%.*}.base.${filename##*.}"
        fi
        
        echo "::notice::Fetching $FILE_PATH from base branch: $BASE_BRANCH"
        
        # Ensure we have the latest base branch
        git fetch origin "$BASE_BRANCH" --depth=1 2>/dev/null || true
        
        # Attempt to fetch the file
        if ! git show "origin/$BASE_BRANCH:$FILE_PATH" > "$base_file" 2>/dev/null; then
          if [ "$FAIL_ON_MISSING" = "true" ]; then
            echo "::error::Failed to fetch $FILE_PATH from base branch $BASE_BRANCH"
            exit 1
          else
            echo "::warning::Failed to fetch $FILE_PATH from base branch $BASE_BRANCH"
            echo "file_exists=false" >> "$GITHUB_OUTPUT"
            echo "file_path=" >> "$GITHUB_OUTPUT"
            echo "file_content=" >> "$GITHUB_OUTPUT"
            exit 0
          fi
        fi
        
        # Check if file is empty
        if [ ! -s "$base_file" ]; then
          if [ "$FAIL_ON_MISSING" = "true" ]; then
            echo "::error::Fetched file $base_file is empty"
            exit 1
          else
            echo "::warning::Fetched file $base_file is empty"
            echo "file_exists=false" >> "$GITHUB_OUTPUT"
            echo "file_path=" >> "$GITHUB_OUTPUT"
            echo "file_content=" >> "$GITHUB_OUTPUT"
            exit 0
          fi
        fi
        
        # Validate JSON if requested
        if [ "$VALIDATE_JSON" = "true" ]; then
          if ! jq empty "$base_file" 2>/dev/null; then
            if [ "$FAIL_ON_MISSING" = "true" ]; then
              echo "::error::File $base_file is not valid JSON"
              cat "$base_file"
              exit 1
            else
              echo "::warning::File $base_file is not valid JSON"
              echo "file_exists=false" >> "$GITHUB_OUTPUT"
              echo "file_path=" >> "$GITHUB_OUTPUT"
              echo "file_content=" >> "$GITHUB_OUTPUT"
              exit 0
            fi
          fi
        fi
        
        # Output file path
        echo "file_path=$base_file" >> "$GITHUB_OUTPUT"
        echo "file_exists=true" >> "$GITHUB_OUTPUT"
        
        # Output content if requested
        if [ "$OUTPUT_CONTENT" = "true" ]; then
          if [ "$VALIDATE_JSON" = "true" ]; then
            content=$(jq -c . "$base_file")
            {
              echo 'file_content<<EOF'
              echo "$content"
              echo 'EOF'
            } >> "$GITHUB_OUTPUT"
          else
            {
              echo 'file_content<<EOF'
              cat "$base_file"
              echo 'EOF'
            } >> "$GITHUB_OUTPUT"
          fi
        fi
        
        echo "::notice::Successfully fetched $FILE_PATH to $base_file"
```

### Step 3: Create `README.md`

```markdown
# Fetch Base File Action

Fetches and validates a file from a base branch using `git show`.

## Usage

### Basic Usage

```yaml
- name: Fetch base descriptor
  id: fetch-descriptor
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@master
  with:
    base_branch: R1-2025
    file_path: platform-descriptor.json
```

### Advanced Usage

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

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `base_branch` | Base branch to fetch from | Yes | - |
| `file_path` | Path to file in repository | Yes | - |
| `output_filename` | Custom output filename | No | `<file>.base.<ext>` |
| `validate_json` | Validate file as JSON | No | `true` |
| `fail_on_missing` | Fail if file missing | No | `true` |
| `output_content` | Output file content | No | `false` |

## Outputs

| Output | Description | Example |
|--------|-------------|---------|
| `file_path` | Path to fetched file | `platform-descriptor.base.json` |
| `file_exists` | Whether file exists | `true` or `false` |
| `file_content` | File content (if requested) | `{"version": "1.0"}` |

## Behavior

### Success Path
1. Fetches latest base branch metadata
2. Uses `git show` to extract file
3. Validates file is not empty
4. Optionally validates JSON structure
5. Optionally outputs content
6. Returns file path and status

### Error Handling

**When `fail_on_missing=true` (default):**
- Missing file → Error, workflow fails
- Empty file → Error, workflow fails
- Invalid JSON → Error, workflow fails

**When `fail_on_missing=false`:**
- Missing file → Warning, `file_exists=false`
- Empty file → Warning, `file_exists=false`
- Invalid JSON → Warning, `file_exists=false`

## Requirements

- Git repository must be checked out
- Base branch must exist in remote
- `jq` required if `validate_json=true`
```

### Step 4: Update Workflow - Instance 1

Replace in `update-platform-descriptor` job:

```yaml
# Before
- name: 'Fetch and save base branch descriptor'
  id: fetch-base-descriptor
  env:
    RELEASE_BRANCH: ${{ inputs.release_branch }}
    STATE_FILE: ${{ env.STATE_FILE }}
  run: |
    # ...40 lines of bash...

# After
- name: 'Fetch base descriptor'
  id: fetch-base-descriptor
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@RANCHER-2324
  with:
    base_branch: ${{ inputs.release_branch }}
    file_path: ${{ env.STATE_FILE }}
    validate_json: true
    fail_on_missing: true
```

### Step 5: Update Workflow - Instance 2

Replace in `update-package-json` job:

```yaml
# Before
- name: 'Fetch base branch package.json'
  id: fetch-base-package-json
  env:
    RELEASE_BRANCH: ${{ inputs.release_branch }}
  run: |
    # ...40 lines of bash...

# After
- name: 'Fetch base package.json'
  id: fetch-base-package-json
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@RANCHER-2324
  with:
    base_branch: ${{ inputs.release_branch }}
    file_path: package.json
    output_filename: package.json.base
    validate_json: true
    fail_on_missing: false
    output_content: true
```

### Step 6: Update Output References

Update any references to outputs:

```yaml
# Update from:
base_state_file: ${{ steps.fetch-base-descriptor.outputs.base_state_file }}

# To:
base_state_file: ${{ steps.fetch-base-descriptor.outputs.file_path }}
```

---

## Testing Strategy

### Test Scenarios

1. **File exists and is valid JSON**
   - Expected: file_exists=true, file_path populated, valid content

2. **File does not exist (fail_on_missing=true)**
   - Expected: Error, workflow fails

3. **File does not exist (fail_on_missing=false)**
   - Expected: Warning, file_exists=false

4. **File exists but is empty**
   - Expected: Behavior depends on fail_on_missing

5. **File exists but invalid JSON (validate_json=true)**
   - Expected: Behavior depends on fail_on_missing

6. **Non-JSON file (validate_json=false)**
   - Expected: file_exists=true, content returned as-is

7. **Output content enabled**
   - Expected: file_content populated with file contents

### Test Workflow Example

```yaml
name: Test Fetch Base File
on: workflow_dispatch

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Test valid JSON file
        id: test1
        uses: ./.github/actions/fetch-base-file
        with:
          base_branch: master
          file_path: package.json
          validate_json: true
      
      - name: Validate output
        run: |
          if [ "${{ steps.test1.outputs.file_exists }}" != "true" ]; then
            echo "Test failed: file should exist"
            exit 1
          fi
          if [ ! -f "${{ steps.test1.outputs.file_path }}" ]; then
            echo "Test failed: file not found at path"
            exit 1
          fi
      
      - name: Test missing file (no fail)
        id: test2
        uses: ./.github/actions/fetch-base-file
        with:
          base_branch: master
          file_path: nonexistent.json
          fail_on_missing: false
      
      - name: Validate missing file handling
        run: |
          if [ "${{ steps.test2.outputs.file_exists }}" != "false" ]; then
            echo "Test failed: file should not exist"
            exit 1
          fi
```

---

## Success Criteria

- [ ] Action directory created with proper structure
- [ ] `action.yml` implements all specified inputs/outputs
- [ ] `README.md` documents usage with examples
- [ ] Both workflow instances updated to use action
- [ ] All test scenarios pass
- [ ] Outputs correctly mapped in workflow
- [ ] No regression in functionality
- [ ] Code follows FOLIO safe shell practices

---

## Integration Checklist

- [ ] Create action files (action.yml, README.md)
- [ ] Test action with various scenarios
- [ ] Update first workflow instance (platform descriptor)
- [ ] Verify first instance works correctly
- [ ] Update second workflow instance (package.json)
- [ ] Verify second instance works correctly
- [ ] Update output reference mappings
- [ ] Run full workflow with dry_run=true
- [ ] Run workflow in production
- [ ] Document action in main README

---

## Migration Notes

### Output Name Changes

| Old Output | New Output | Job |
|------------|------------|-----|
| `base_state_file` | `file_path` | update-platform-descriptor |
| `base_package_json_file` | `file_path` | update-package-json |
| `base_package_json_content` | `file_content` | update-package-json |
| `base_package_json_exists` | `file_exists` | update-package-json |

### Behavior Differences

- **Auto-naming:** If `output_filename` not specified, uses pattern `<name>.base.<ext>`
- **Consistent errors:** Both instances now use same error handling logic
- **Git fetch:** Always attempts to fetch latest base branch

---

**Implementation Priority:** 🔴 High  
**Estimated Effort:** 2-3 hours  
**Dependencies:** None  
**Previous Action:** [Action #1: check-branch-and-pr-status](./01-check-branch-and-pr-status.md)  
**Next Action:** [Action #3: generate-platform-diff-report](./03-generate-platform-diff-report.md)

