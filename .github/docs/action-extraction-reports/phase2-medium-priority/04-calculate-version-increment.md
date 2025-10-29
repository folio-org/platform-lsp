# Action Extraction Report #4: calculate-version-increment

**Phase:** 2 (Medium Priority)  
**Complexity Reduction:** ~30 lines  
**Impact:** Medium  
**Implementation Time:** 1-2 hours

---

## Overview

### Purpose
Calculates a new semantic version number based on whether changes were detected. Implements FOLIO's release versioning pattern: `R<iteration>-<year>.<patch>`.

### Current Problem
Version calculation logic (~30 lines) is embedded in the `update-platform-descriptor` job. While not extremely complex, it's a discrete logical operation that could be:
- Reused in other versioning contexts
- Extended to support different version schemes
- Tested independently

### Benefits of Extraction
- **Reusability:** Version logic available for other workflows
- **Extensibility:** Easy to support multiple version patterns
- **Testability:** Can unit test version increment logic
- **Single Responsibility:** Clear separation of versioning concern

---

## Current Implementation

### Location in Workflow
**File:** `.github/workflows/release-update-flow.yml`  
**Job:** `update-platform-descriptor`  
**Step:** "Calculate New Version"

### Current Code

```yaml
- name: 'Calculate New Version'
  id: calculate-new-version
  env:
    PREVIOUS_VERSION: ${{ steps.compare-components.outputs.previous_version }}
    CHANGES_DETECTED: ${{ steps.compare-components.outputs.changes_detected }}
  run: |
    set -euo pipefail
    IFS=$'\n\t'
    UPDATED=false
    FAILURE_REASON=''
    NEW_VERSION="$PREVIOUS_VERSION"
    if [ "$CHANGES_DETECTED" = 'true' ]; then
      if [[ "$PREVIOUS_VERSION" =~ ^(R[0-9]+-[0-9]+)\.([0-9]+)$ ]]; then
        BASE_VERSION="${BASH_REMATCH[1]}"
        PATCH_VERSION="${BASH_REMATCH[2]}"
        NEW_VERSION="${BASE_VERSION}.$((PATCH_VERSION + 1))"
        UPDATED=true
        echo "::notice::Calculated new version $NEW_VERSION from previous $PREVIOUS_VERSION"
      else
        FAILURE_REASON="Previous version '$PREVIOUS_VERSION' does not match expected format 'R<iteration>-<year>.<patch>'"
        echo "::warning::$FAILURE_REASON (no update applied)"
        UPDATED=false
      fi
    else
      echo '::notice::No component/application changes detected; version unchanged'
    fi
    echo "updated=$UPDATED" >> "$GITHUB_OUTPUT"
    echo "new_version=$NEW_VERSION" >> "$GITHUB_OUTPUT"
    echo "failure_reason=$FAILURE_REASON" >> "$GITHUB_OUTPUT"
```

### Complexity Analysis
- **Lines:** ~30 lines
- **Logic:** Regex pattern matching, arithmetic increment
- **Dependencies:** Bash built-ins only
- **Extensibility:** Could support multiple patterns

---

## Action Specification

### Inputs

```yaml
inputs:
  current_version:
    description: 'Current version string (e.g., R1-2025.3)'
    required: true
  
  changes_detected:
    description: 'Whether changes were detected (true/false)'
    required: true
  
  version_pattern:
    description: 'Regex pattern for version matching'
    required: false
    default: '^(R[0-9]+-[0-9]+)\.([0-9]+)$'
  
  increment_type:
    description: 'Type of increment (patch, minor, major)'
    required: false
    default: 'patch'
```

### Outputs

```yaml
outputs:
  new_version:
    description: 'Calculated new version'
    value: ${{ steps.calculate.outputs.new_version }}
  
  updated:
    description: 'Whether version was incremented (true/false)'
    value: ${{ steps.calculate.outputs.updated }}
  
  failure_reason:
    description: 'Error message if version calculation failed'
    value: ${{ steps.calculate.outputs.failure_reason }}
```

---

## Implementation Guide

### action.yml

```yaml
name: 'Calculate Version Increment'
description: 'Calculates new semantic version based on changes'
author: 'FOLIO DevOps'

inputs:
  current_version:
    description: 'Current version'
    required: true
  changes_detected:
    description: 'Whether changes detected'
    required: true
  version_pattern:
    description: 'Regex pattern'
    required: false
    default: '^(R[0-9]+-[0-9]+)\.([0-9]+)$'
  increment_type:
    description: 'Increment type'
    required: false
    default: 'patch'

outputs:
  new_version:
    description: 'New version'
    value: ${{ steps.calculate.outputs.new_version }}
  updated:
    description: 'Whether updated'
    value: ${{ steps.calculate.outputs.updated }}
  failure_reason:
    description: 'Failure reason'
    value: ${{ steps.calculate.outputs.failure_reason }}

runs:
  using: 'composite'
  steps:
    - name: 'Calculate version'
      id: calculate
      shell: bash
      env:
        CURRENT_VERSION: ${{ inputs.current_version }}
        CHANGES_DETECTED: ${{ inputs.changes_detected }}
        VERSION_PATTERN: ${{ inputs.version_pattern }}
        INCREMENT_TYPE: ${{ inputs.increment_type }}
      run: |
        set -euo pipefail
        IFS=$'\n\t'
        
        UPDATED=false
        FAILURE_REASON=''
        NEW_VERSION="$CURRENT_VERSION"
        
        if [ "$CHANGES_DETECTED" = 'true' ]; then
          if [[ "$CURRENT_VERSION" =~ $VERSION_PATTERN ]]; then
            BASE_VERSION="${BASH_REMATCH[1]}"
            PATCH_VERSION="${BASH_REMATCH[2]}"
            
            case "$INCREMENT_TYPE" in
              patch)
                NEW_VERSION="${BASE_VERSION}.$((PATCH_VERSION + 1))"
                ;;
              *)
                FAILURE_REASON="Unsupported increment type: $INCREMENT_TYPE"
                echo "::warning::$FAILURE_REASON"
                ;;
            esac
            
            if [ "$NEW_VERSION" != "$CURRENT_VERSION" ]; then
              UPDATED=true
              echo "::notice::Calculated new version $NEW_VERSION from $CURRENT_VERSION"
            fi
          else
            FAILURE_REASON="Version '$CURRENT_VERSION' does not match pattern '$VERSION_PATTERN'"
            echo "::warning::$FAILURE_REASON (no update applied)"
          fi
        else
          echo '::notice::No changes detected; version unchanged'
        fi
        
        echo "updated=$UPDATED" >> "$GITHUB_OUTPUT"
        echo "new_version=$NEW_VERSION" >> "$GITHUB_OUTPUT"
        echo "failure_reason=$FAILURE_REASON" >> "$GITHUB_OUTPUT"
```

### Usage in Workflow

```yaml
- name: 'Calculate new version'
  id: calculate-new-version
  uses: folio-org/platform-lsp/.github/actions/calculate-version-increment@RANCHER-2324
  with:
    current_version: ${{ steps.compare-components.outputs.previous_version }}
    changes_detected: ${{ steps.compare-components.outputs.changes_detected }}
```

---

## Testing Strategy

### Test Scenarios

1. **No changes** → version unchanged
2. **Changes + valid version** → version incremented
3. **Changes + invalid version** → failure_reason set, no increment
4. **Different patterns** → custom pattern support

### Test Script

```bash
# Test 1: No changes
CURRENT_VERSION=R1-2025.5 CHANGES_DETECTED=false VERSION_PATTERN='^(R[0-9]+-[0-9]+)\.([0-9]+)$' INCREMENT_TYPE=patch bash action-script.sh
# Expected: new_version=R1-2025.5, updated=false

# Test 2: Changes detected
CURRENT_VERSION=R1-2025.5 CHANGES_DETECTED=true VERSION_PATTERN='^(R[0-9]+-[0-9]+)\.([0-9]+)$' INCREMENT_TYPE=patch bash action-script.sh
# Expected: new_version=R1-2025.6, updated=true

# Test 3: Invalid version
CURRENT_VERSION=invalid CHANGES_DETECTED=true VERSION_PATTERN='^(R[0-9]+-[0-9]+)\.([0-9]+)$' INCREMENT_TYPE=patch bash action-script.sh
# Expected: new_version=invalid, updated=false, failure_reason set
```

---

## Success Criteria

- [ ] Action created with proper structure
- [ ] All test scenarios pass
- [ ] Workflow integrated successfully
- [ ] Documentation complete
- [ ] Pattern matching flexible for future use

---

**Implementation Priority:** 🟡 Medium  
**Estimated Effort:** 1-2 hours  
**Previous Action:** [Action #3: generate-platform-diff-report](../phase1-high-priority/03-generate-platform-diff-report.md)  
**Next Action:** [Action #5: generate-package-diff-report](./05-generate-package-diff-report.md)

