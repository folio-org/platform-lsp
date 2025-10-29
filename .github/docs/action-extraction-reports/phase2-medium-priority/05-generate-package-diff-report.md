# Action Extraction Report #5: generate-package-diff-report

**Phase:** 2 (Medium Priority)  
**Complexity Reduction:** ~80 lines  
**Impact:** Medium  
**Implementation Time:** 3-4 hours

---

## Overview

### Purpose
Generates a collapsed diff and formatted markdown report comparing `package.json` dependencies between base and head branches. Similar to the platform diff report but focused on npm dependencies.

### Current Problem
The logic is split across two steps (~80 lines total) in the `generate-reports` job:
- "Build collapsed UI dependencies diff" - calculates the diff
- "Generate Collapsed Markdown Report" (partial) - renders markdown

This duplicates the pattern established by `generate-platform-diff-report` and should follow the same extraction approach.

### Benefits of Extraction
- **Consistency:** Matches pattern of platform-diff-report
- **Reusability:** Useful for any package.json comparison
- **Maintainability:** Centralized npm diff logic
- **Testability:** Independent testing of dependency diff

---

## Current Implementation

### Location in Workflow
**File:** `.github/workflows/release-update-flow.yml`  
**Job:** `generate-reports`  
**Step:** "Build collapsed UI dependencies diff" + partial "Generate Collapsed Markdown Report"

### Current Code (Abbreviated)

```yaml
- name: 'Build collapsed UI dependencies diff'
  id: build-ui-diff
  if: needs.update-package-json.result == 'success'
  run: |
    set -euo pipefail
    IFS=$'\n\t'
    
    # Find base package.json
    BASE_PACKAGE_JSON_FILE=$(find . -maxdepth 1 -name "package.json.base" -o -name "package.*.base" | head -n 1)
    
    # Read base and current package.json
    BASE_DEPS=$(echo "$BASE_PACKAGE_JSON_CONTENT" | jq -c '.dependencies // {}')
    UPDATED_DEPS=$(echo "$UPDATED_PACKAGE_JSON_CONTENT" | jq -c '.dependencies // {}')
    
    # Build collapsed diff showing only changes
    COLLAPSED_UI_DIFF=$(jq -n \
      --argjson base "$BASE_DEPS" \
      --argjson updated "$UPDATED_DEPS" '
      [
        ($base | keys[]) as $k |
        select(
          ($updated | has($k)) and
          ($base[$k] != $updated[$k])
        ) |
        {
          name: $k,
          change: {
            old: $base[$k],
            new: $updated[$k]
          }
        }
      ]
    ')
    
    UI_UPDATES_CNT=$(jq 'length' <<< "$COLLAPSED_UI_DIFF")
    # ...output to GITHUB_OUTPUT

# Markdown rendering
render_ui_table() {
  local json="$1"
  # ...validation
  echo '| Dependency | Old Version | New Version |'
  echo '| ---------- | ----------- | ----------- |'
  jq -r '.[] | "| \(.name) | \(.change.old) | \(.change.new) |"' <<< "$json"
}

ui_table=$(render_ui_table "${COLLAPSED_UI_DIFF}")
ui_updates_markdown=$(cat <<EOF
### UI Dependency Updates
**Base branch:** ${RELEASE_BRANCH}
**Head branch:** ${UPDATE_BRANCH}
**Updated dependencies:** ${ui_count}
${ui_table}
> This table shows the collapsed diff of \`package.json\` dependencies.
EOF
)
```

### Complexity Analysis
- **Lines:** ~80 lines across 2 steps
- **Dependencies:** `jq`, `find`
- **Logic:** JSON diff, markdown table rendering
- **Similarity to Action #3:** ~90% similar pattern

---

## Action Specification

### Inputs

```yaml
inputs:
  base_package_path:
    description: 'Path to base package.json file'
    required: true
  
  head_package_path:
    description: 'Path to head package.json file'
    required: true
  
  release_branch:
    description: 'Base branch name for display'
    required: true
  
  update_branch:
    description: 'Head branch name for display'
    required: true
  
  dependency_type:
    description: 'Dependency type to compare (dependencies, devDependencies, all)'
    required: false
    default: 'dependencies'
```

### Outputs

```yaml
outputs:
  ui_updates_markdown:
    description: 'Formatted markdown report of dependency changes'
    value: ${{ steps.generate.outputs.ui_updates_markdown }}
  
  ui_updates_cnt:
    description: 'Number of dependency changes'
    value: ${{ steps.generate.outputs.ui_updates_cnt }}
  
  diff_json:
    description: 'JSON array of dependency changes'
    value: ${{ steps.generate.outputs.diff_json }}
  
  has_changes:
    description: 'Whether any changes detected'
    value: ${{ steps.generate.outputs.has_changes }}
```

---

## Implementation Guide

### Step 1: Create Action Structure

```bash
mkdir -p .github/actions/generate-package-diff-report/scripts
cd .github/actions/generate-package-diff-report
```

### Step 2: Create `action.yml`

```yaml
name: 'Generate Package Diff Report'
description: 'Generates collapsed diff and markdown for package.json dependencies'
author: 'FOLIO DevOps'

inputs:
  base_package_path:
    description: 'Path to base package.json'
    required: true
  head_package_path:
    description: 'Path to head package.json'
    required: true
  release_branch:
    description: 'Base branch name'
    required: true
  update_branch:
    description: 'Head branch name'
    required: true
  dependency_type:
    description: 'Dependency type to compare'
    required: false
    default: 'dependencies'

outputs:
  ui_updates_markdown:
    description: 'Markdown report'
    value: ${{ steps.generate.outputs.ui_updates_markdown }}
  ui_updates_cnt:
    description: 'Number of changes'
    value: ${{ steps.generate.outputs.ui_updates_cnt }}
  diff_json:
    description: 'JSON diff'
    value: ${{ steps.generate.outputs.diff_json }}
  has_changes:
    description: 'Has changes'
    value: ${{ steps.generate.outputs.has_changes }}

runs:
  using: 'composite'
  steps:
    - name: 'Generate package diff and markdown'
      id: generate
      shell: bash
      env:
        BASE_PACKAGE: ${{ inputs.base_package_path }}
        HEAD_PACKAGE: ${{ inputs.head_package_path }}
        RELEASE_BRANCH: ${{ inputs.release_branch }}
        UPDATE_BRANCH: ${{ inputs.update_branch }}
        DEPENDENCY_TYPE: ${{ inputs.dependency_type }}
      run: ${{ github.action_path }}/scripts/generate-package-diff.sh
```

### Step 3: Create `scripts/generate-package-diff.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Validate files exist
if [ ! -f "$BASE_PACKAGE" ]; then
  echo "::warning::Base package.json not found: $BASE_PACKAGE"
  echo 'ui_updates_markdown=### UI Dependency Updates\n\n_Base package.json not available._' >> "$GITHUB_OUTPUT"
  echo 'ui_updates_cnt=0' >> "$GITHUB_OUTPUT"
  echo 'diff_json=[]' >> "$GITHUB_OUTPUT"
  echo 'has_changes=false' >> "$GITHUB_OUTPUT"
  exit 0
fi

if [ ! -f "$HEAD_PACKAGE" ]; then
  echo "::error::Head package.json not found: $HEAD_PACKAGE"
  exit 1
fi

echo "::notice::Generating package diff between $BASE_PACKAGE and $HEAD_PACKAGE"

# Determine jq path for dependency type
case "$DEPENDENCY_TYPE" in
  dependencies)
    DEP_PATH=".dependencies // {}"
    ;;
  devDependencies)
    DEP_PATH=".devDependencies // {}"
    ;;
  all)
    DEP_PATH="(.dependencies // {}) + (.devDependencies // {})"
    ;;
  *)
    echo "::error::Invalid dependency_type: $DEPENDENCY_TYPE"
    exit 1
    ;;
esac

# Extract dependencies
BASE_DEPS=$(jq -c "$DEP_PATH" "$BASE_PACKAGE")
HEAD_DEPS=$(jq -c "$DEP_PATH" "$HEAD_PACKAGE")

# Build diff
DIFF_JSON=$(jq -n \
  --argjson base "$BASE_DEPS" \
  --argjson head "$HEAD_DEPS" '
  [
    ($base | keys[]) as $k |
    select(
      ($head | has($k)) and
      ($base[$k] != $head[$k])
    ) |
    {
      name: $k,
      change: {
        old: $base[$k],
        new: $head[$k]
      }
    }
  ]
')

UPDATES_CNT=$(jq 'length' <<< "$DIFF_JSON")
HAS_CHANGES="false"
[ "$UPDATES_CNT" -gt 0 ] && HAS_CHANGES="true"

echo "::notice::Found $UPDATES_CNT dependency changes"

# Render markdown
if [ "$HAS_CHANGES" = "false" ]; then
  MARKDOWN=$'### UI Dependency Updates\n\n_No changes detected between base and head package.json._'
else
  TABLE=$(cat <<'EOFTABLE'
| Dependency | Old Version | New Version |
| ---------- | ----------- | ----------- |
EOFTABLE
  )
  
  TABLE_ROWS=$(jq -r '.[] | "| \(.name) | \(.change.old) | \(.change.new) |"' <<< "$DIFF_JSON")
  
  MARKDOWN=$(cat <<EOF
### UI Dependency Updates

**Base branch:** ${RELEASE_BRANCH}
**Head branch:** ${UPDATE_BRANCH}
**Updated dependencies:** ${UPDATES_CNT}

${TABLE}
${TABLE_ROWS}

> This table shows the collapsed diff of \`package.json\` dependencies between base and head branches.
EOF
  )
fi

# Output
{
  echo 'ui_updates_markdown<<EOF'
  echo "$MARKDOWN"
  echo 'EOF'
} >> "$GITHUB_OUTPUT"

{
  echo 'diff_json<<EOF'
  echo "$DIFF_JSON"
  echo 'EOF'
} >> "$GITHUB_OUTPUT"

echo "ui_updates_cnt=$UPDATES_CNT" >> "$GITHUB_OUTPUT"
echo "has_changes=$HAS_CHANGES" >> "$GITHUB_OUTPUT"

echo "::notice::Package diff report generated"
```

Make executable:
```bash
chmod +x scripts/generate-package-diff.sh
```

### Step 4: Update Workflow

Replace in `generate-reports` job:

```yaml
# Before
- name: 'Build collapsed UI dependencies diff'
  id: build-ui-diff
  # ...~80 lines...

# After
- name: 'Generate package diff report'
  id: build-ui-diff
  if: needs.update-package-json.result == 'success'
  uses: folio-org/platform-lsp/.github/actions/generate-package-diff-report@RANCHER-2324
  with:
    base_package_path: ${{ steps.find-base-package.outputs.file_path }}
    head_package_path: package.json
    release_branch: ${{ inputs.release_branch }}
    update_branch: ${{ inputs.update_branch }}
    dependency_type: dependencies
```

---

## Testing Strategy

### Test Scenarios

1. **No changes** → Empty diff, appropriate message
2. **Changes in dependencies** → Correct diff and count
3. **Base file missing** → Warning, graceful handling
4. **Head file missing** → Error
5. **Different dependency types** → Correct filtering

### Test Script

```bash
# Create test files
cat > base-test.json <<'EOF'
{
  "dependencies": {
    "@folio/stripes": "^9.0.0",
    "react": "^18.2.0"
  }
}
EOF

cat > head-test.json <<'EOF'
{
  "dependencies": {
    "@folio/stripes": "^9.1.0",
    "react": "^18.2.0"
  }
}
EOF

# Run script
BASE_PACKAGE=base-test.json \
HEAD_PACKAGE=head-test.json \
RELEASE_BRANCH=R1-2025 \
UPDATE_BRANCH=R1-2025-update \
DEPENDENCY_TYPE=dependencies \
./scripts/generate-package-diff.sh

# Should show 1 change (@folio/stripes version bump)
```

---

## Success Criteria

- [ ] Action created with script structure
- [ ] Script executable and follows standards
- [ ] All test scenarios pass
- [ ] Workflow updated successfully
- [ ] Output format matches previous
- [ ] Handles missing files gracefully
- [ ] Documentation complete

---

**Implementation Priority:** 🟡 Medium  
**Estimated Effort:** 3-4 hours  
**Dependencies:** Similar to Action #3  
**Previous Action:** [Action #4: calculate-version-increment](./04-calculate-version-increment.md)  
**Next Action:** [Action #6: build-pr-body](./06-build-pr-body.md)

