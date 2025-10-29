# Action Extraction Report #3: generate-platform-diff-report

**Phase:** 1 (High Priority)  
**Complexity Reduction:** ~200 lines  
**Impact:** Very High  
**Implementation Time:** 4-6 hours

---

## Overview

### Purpose
Generates a collapsed diff and formatted markdown report comparing platform descriptors (eureka-components and applications) between a base branch and head branch. This is the most complex inline logic in the workflow.

### Current Problem
The step "Build Collapsed Diff Report" contains ~100 lines of complex Bash with:
- Nested jq transformations for diff calculation
- Helper function definitions
- Multiple JSON manipulations
- Markdown table rendering (another ~100 lines in "Generate Collapsed Markdown Report")

This makes the workflow extremely difficult to maintain and test.

### Benefits of Extraction
- **Massive Complexity Reduction:** 200+ lines → single action call
- **Testability:** Can unit test diff logic independently
- **Reusability:** Useful for any platform descriptor comparison
- **Maintainability:** Changes to diff/rendering logic in one place

---

## Current Implementation

### Location in Workflow
**File:** `.github/workflows/release-update-flow.yml`  
**Job:** `generate-reports`  
**Steps:** "Build Collapsed Diff Report" + "Generate Collapsed Markdown Report" (partial)

### Current Code (Abbreviated)

```bash
# Build Collapsed Diff Report (Base vs Head)
collapse_lists() {
  local base_json="$1"
  local head_json="$2"
  local label="$3"
  jq -n \
    --argjson B "$base_json" \
    --argjson H "$head_json" \
    --arg label "$label" '
    def to_map: map({key:.name, value:.version}) | from_entries;
    ($B | to_map) as $BM |
    ($H | to_map) as $HM |
    [
      ($BM | keys[]) as $k |
      select(($HM | has($k)) and ($BM[$k] != $HM[$k])) |
      {
        name: $k,
        change: { old: $BM[$k], new: $HM[$k] },
        group: $label
      }
    ]
  '
}

# Extract and compare all sections
BASE_EC=$(jq -c '."eureka-components"' "$BASE_STATE_FILE")
# ... (similar for applications.required, applications.optional)
EC_DIFF=$(collapse_lists "$BASE_EC" "$HEAD_EC" "Eureka Components")
# ... (combine diffs)

# Generate Markdown
render_collapsed_table() {
  local json="$1"
  # ~30 lines of table rendering logic
  echo '| Name | Old Version | New Version | Group |'
  jq -r '.[] | "| \(.name) | \(.change.old) | \(.change.new) | \(.group) |"' <<< "$json"
}

descriptor_table=$(render_collapsed_table "${UPDATED_REPORT}")
descriptor_markdown=$(cat <<EOF
### Application & Component Updates
**Base branch:** ${RELEASE_BRANCH}
**Changed entries:** ${UPDATES_CNT}
${descriptor_table}
EOF
)
```

### Complexity Analysis
- **Total lines:** ~200 lines across 2 steps
- **Functions:** 2 helper functions (collapse_lists, render_collapsed_table)
- **jq queries:** 3+ complex transformations
- **Dependencies:** `jq`, `find`
- **Inputs:** Base/head descriptor files, branch names
- **Outputs:** Markdown report, diff JSON, update count

---

## Action Specification

### Inputs

```yaml
inputs:
  base_descriptor_path:
    description: 'Path to base platform descriptor JSON file'
    required: true
  
  head_descriptor_path:
    description: 'Path to head platform descriptor JSON file'
    required: true
  
  release_branch:
    description: 'Base branch name for display'
    required: true
  
  update_branch:
    description: 'Head branch name for display'
    required: true
  
  platform_version:
    description: 'Platform version for display'
    required: false
```

### Outputs

```yaml
outputs:
  updates_markdown:
    description: 'Formatted markdown report of changes'
    value: ${{ steps.generate.outputs.updates_markdown }}
  
  updates_cnt:
    description: 'Total number of changes detected'
    value: ${{ steps.generate.outputs.updates_cnt }}
  
  diff_json:
    description: 'JSON array of all changes'
    value: ${{ steps.generate.outputs.diff_json }}
  
  has_changes:
    description: 'Whether any changes were detected (true/false)'
    value: ${{ steps.generate.outputs.has_changes }}
```

---

## Implementation Guide

### Step 1: Create Action with Script

```bash
mkdir -p .github/actions/generate-platform-diff-report/scripts
cd .github/actions/generate-platform-diff-report
```

### Step 2: Create `action.yml`

```yaml
name: 'Generate Platform Diff Report'
description: 'Generates collapsed diff and markdown for platform descriptors'
author: 'FOLIO DevOps'

inputs:
  base_descriptor_path:
    description: 'Path to base platform descriptor'
    required: true
  head_descriptor_path:
    description: 'Path to head platform descriptor'
    required: true
  release_branch:
    description: 'Base branch name'
    required: true
  update_branch:
    description: 'Head branch name'
    required: true
  platform_version:
    description: 'Platform version'
    required: false

outputs:
  updates_markdown:
    description: 'Markdown report'
    value: ${{ steps.generate.outputs.updates_markdown }}
  updates_cnt:
    description: 'Number of changes'
    value: ${{ steps.generate.outputs.updates_cnt }}
  diff_json:
    description: 'JSON diff'
    value: ${{ steps.generate.outputs.diff_json }}
  has_changes:
    description: 'Has changes'
    value: ${{ steps.generate.outputs.has_changes }}

runs:
  using: 'composite'
  steps:
    - name: 'Generate diff and markdown report'
      id: generate
      shell: bash
      env:
        BASE_DESCRIPTOR: ${{ inputs.base_descriptor_path }}
        HEAD_DESCRIPTOR: ${{ inputs.head_descriptor_path }}
        RELEASE_BRANCH: ${{ inputs.release_branch }}
        UPDATE_BRANCH: ${{ inputs.update_branch }}
        PLATFORM_VERSION: ${{ inputs.platform_version }}
      run: ${{ github.action_path }}/scripts/generate-diff.sh
```

### Step 3: Create `scripts/generate-diff.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Validate input files exist
if [ ! -f "$BASE_DESCRIPTOR" ]; then
  echo "::error::Base descriptor not found: $BASE_DESCRIPTOR"
  exit 1
fi

if [ ! -f "$HEAD_DESCRIPTOR" ]; then
  echo "::error::Head descriptor not found: $HEAD_DESCRIPTOR"
  exit 1
fi

echo "::notice::Generating diff between $BASE_DESCRIPTOR and $HEAD_DESCRIPTOR"

# Function to collapse changes for a list
collapse_lists() {
  local base_json="$1"
  local head_json="$2"
  local label="$3"
  
  jq -n \
    --argjson B "$base_json" \
    --argjson H "$head_json" \
    --arg label "$label" '
    def to_map: map({key:.name, value:.version}) | from_entries;
    ($B | to_map) as $BM |
    ($H | to_map) as $HM |
    [
      ($BM | keys[]) as $k |
      select(($HM | has($k)) and ($BM[$k] != $HM[$k])) |
      {
        name: $k,
        change: { old: $BM[$k], new: $HM[$k] },
        group: $label
      }
    ]
  '
}

# Extract components from base
BASE_EC=$(jq -c '."eureka-components"' "$BASE_DESCRIPTOR")
BASE_REQ=$(jq -c '.applications.required' "$BASE_DESCRIPTOR")
BASE_OPT=$(jq -c '.applications.optional' "$BASE_DESCRIPTOR")

# Extract components from head
HEAD_EC=$(jq -c '."eureka-components"' "$HEAD_DESCRIPTOR")
HEAD_REQ=$(jq -c '.applications.required' "$HEAD_DESCRIPTOR")
HEAD_OPT=$(jq -c '.applications.optional' "$HEAD_DESCRIPTOR")

# Build diffs
EC_DIFF=$(collapse_lists "$BASE_EC" "$HEAD_EC" "Eureka Components")
REQ_DIFF=$(collapse_lists "$BASE_REQ" "$HEAD_REQ" "Applications (required)")
OPT_DIFF=$(collapse_lists "$BASE_OPT" "$HEAD_OPT" "Applications (optional)")

# Combine all diffs
COLLAPSED_REPORT=$(jq -n \
  --argjson a "$EC_DIFF" \
  --argjson b "$REQ_DIFF" \
  --argjson c "$OPT_DIFF" \
  '$a + $b + $c')

UPDATES_CNT=$(jq 'length' <<< "$COLLAPSED_REPORT")
HAS_CHANGES="false"
[ "$UPDATES_CNT" -gt 0 ] && HAS_CHANGES="true"

echo "::notice::Found $UPDATES_CNT changes"

# Function to render markdown table
render_table() {
  local json="$1"
  if [ -z "${json:-}" ] || [ "$json" = "[]" ]; then
    echo ''
    return 0
  fi
  local count
  if ! count=$(jq 'length' <<< "$json" 2>/dev/null) || [ "$count" -eq 0 ]; then
    echo ''
    return 0
  fi
  echo '| Name | Old Version | New Version | Group |'
  echo '| ---- | ----------- | ----------- | ----- |'
  jq -r '.[] | "| \(.name) | \(.change.old) | \(.change.new) | \(.group) |"' <<< "$json"
}

# Generate markdown
if [ "$HAS_CHANGES" = "false" ]; then
  MARKDOWN=$'### Application & Component Updates\n\n_No changes detected between base and head._'
else
  TABLE=$(render_table "$COLLAPSED_REPORT")
  VERSION_LINE=""
  [ -n "${PLATFORM_VERSION:-}" ] && VERSION_LINE="**Platform version:** ${PLATFORM_VERSION}"
  
  MARKDOWN=$(cat <<EOF
### Application & Component Updates

**Base branch:** ${RELEASE_BRANCH}
**Head branch:** ${UPDATE_BRANCH}
${VERSION_LINE}
**Changed entries:** ${UPDATES_CNT}

${TABLE}

> This table shows the collapsed diff of \`platform-descriptor.json\` between base and head branches.
EOF
  )
fi

# Output results
{
  echo 'updates_markdown<<EOF'
  echo "$MARKDOWN"
  echo 'EOF'
} >> "$GITHUB_OUTPUT"

{
  echo 'diff_json<<EOF'
  echo "$COLLAPSED_REPORT"
  echo 'EOF'
} >> "$GITHUB_OUTPUT"

echo "updates_cnt=$UPDATES_CNT" >> "$GITHUB_OUTPUT"
echo "has_changes=$HAS_CHANGES" >> "$GITHUB_OUTPUT"

echo "::notice::Report generated successfully"
```

Make the script executable:
```bash
chmod +x scripts/generate-diff.sh
```

### Step 4: Create `README.md`

See full README in action directory (includes usage examples, inputs/outputs table, requirements).

### Step 5: Update Workflow

Replace in `generate-reports` job:

```yaml
# Before: Steps "Build Collapsed Diff Report" and partial "Generate Collapsed Markdown Report"
- name: 'Build Collapsed Diff Report (Base vs Head)'
  id: build-change-report
  # ...~100 lines...

- name: 'Generate Collapsed Markdown Report'
  id: generate-markdown-reports
  # ...~150 lines (partial, just descriptor part)...

# After:
- name: 'Generate platform diff report'
  id: build-change-report
  uses: folio-org/platform-lsp/.github/actions/generate-platform-diff-report@RANCHER-2324
  with:
    base_descriptor_path: ${{ steps.find-base.outputs.base_file }}
    head_descriptor_path: ${{ env.STATE_FILE }}
    release_branch: ${{ inputs.release_branch }}
    update_branch: ${{ inputs.update_branch }}
    platform_version: ${{ needs.update-platform-descriptor.outputs.new_version }}

- name: 'Set markdown output for job'
  id: set-markdown
  run: |
    {
      echo 'updates_markdown<<EOF'
      echo '${{ steps.build-change-report.outputs.updates_markdown }}'
      echo 'EOF'
    } >> "$GITHUB_OUTPUT"
```

---

## Testing Strategy

### Test Scenarios

1. **No changes between base and head**
   - Expected: has_changes=false, updates_cnt=0, markdown shows "no changes"

2. **Changes in eureka-components only**
   - Expected: has_changes=true, correct count, table shows component changes

3. **Changes in applications.required only**
   - Expected: Correct grouping in table

4. **Changes in all sections**
   - Expected: Combined diff with proper grouping

5. **Missing file**
   - Expected: Error with clear message

6. **Invalid JSON**
   - Expected: jq error, workflow fails

### Test Command

```bash
# Create test descriptors
cat > base-test.json <<'EOF'
{
  "version": "R1-2025.0",
  "eureka-components": [{"name": "mod-foo", "version": "1.0.0"}],
  "applications": {
    "required": [{"name": "app-bar", "version": "2.0.0"}],
    "optional": []
  }
}
EOF

cat > head-test.json <<'EOF'
{
  "version": "R1-2025.1",
  "eureka-components": [{"name": "mod-foo", "version": "1.1.0"}],
  "applications": {
    "required": [{"name": "app-bar", "version": "2.1.0"}],
    "optional": []
  }
}
EOF

# Run action locally
BASE_DESCRIPTOR=base-test.json \
HEAD_DESCRIPTOR=head-test.json \
RELEASE_BRANCH=R1-2025 \
UPDATE_BRANCH=R1-2025-update \
PLATFORM_VERSION=R1-2025.1 \
./scripts/generate-diff.sh
```

---

## Success Criteria

- [ ] Action directory and script created
- [ ] Script is executable and follows FOLIO shell standards
- [ ] All test scenarios pass
- [ ] Workflow updated to use action
- [ ] Output format matches previous implementation
- [ ] Markdown renders correctly in PR descriptions
- [ ] No performance regression
- [ ] Comprehensive README documentation

---

## Advanced Considerations

### Script Organization
The script could be further split:
- `lib/diff-calculator.sh` - Diff logic
- `lib/markdown-renderer.sh` - Rendering logic
- `generate-diff.sh` - Main orchestrator

This is optional but improves testability.

### Performance
Current implementation processes ~3 JSON sections. For larger descriptors, consider streaming jq processing.

### Error Messages
Enhance error messages to include:
- Which section caused the error
- Line numbers for JSON parsing errors
- Suggestions for fixing common issues

---

**Implementation Priority:** 🔴 Very High  
**Estimated Effort:** 4-6 hours  
**Dependencies:** Actions #1 and #2 recommended first  
**Previous Action:** [Action #2: fetch-base-file](./02-fetch-base-file.md)  
**Next Action:** [Action #4: calculate-version-increment](../../phase2-medium-priority/04-calculate-version-increment.md)

