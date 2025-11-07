# Calculate Version Increment Action

Calculates a new semantic version number based on whether changes were detected. Implements FOLIO's release versioning pattern: `R<iteration>-<year>.<patch>`.

## Purpose

This action provides centralized version increment logic for FOLIO platform releases. It:
- Validates version format against configurable regex patterns
- Increments version number when changes are detected
- Provides clear failure reasons for invalid versions
- Supports future extensibility for different version schemes

## Usage

### Basic Usage

Calculate new version with default FOLIO pattern:

```yaml
- name: Calculate new version
  id: calculate-version
  uses: folio-org/platform-lsp/.github/actions/calculate-version-increment@master
  with:
    current_version: R1-2025.5
    changes_detected: true
```

### Advanced Usage with Custom Pattern

Use a custom version pattern:

```yaml
- name: Calculate new version with custom pattern
  id: calculate-version
  uses: folio-org/platform-lsp/.github/actions/calculate-version-increment@master
  with:
    current_version: v2.1.3
    changes_detected: true
    version_pattern: '^v([0-9]+)\.([0-9]+)\.([0-9]+)$'
    increment_type: patch
```

### Complete Workflow Example

```yaml
- name: Compare components
  id: compare-components
  run: |
    # ... component comparison logic ...
    echo "previous_version=R1-2025.5" >> "$GITHUB_OUTPUT"
    echo "changes_detected=true" >> "$GITHUB_OUTPUT"

- name: Calculate new version
  id: calculate-new-version
  uses: folio-org/platform-lsp/.github/actions/calculate-version-increment@master
  with:
    current_version: ${{ steps.compare-components.outputs.previous_version }}
    changes_detected: ${{ steps.compare-components.outputs.changes_detected }}

- name: Use new version
  if: steps.calculate-new-version.outputs.updated == 'true'
  run: |
    echo "New version: ${{ steps.calculate-new-version.outputs.new_version }}"
    echo "Version was updated: ${{ steps.calculate-new-version.outputs.updated }}"

- name: Handle version calculation failure
  if: steps.calculate-new-version.outputs.failure_reason != ''
  run: |
    echo "::warning::Version calculation failed: ${{ steps.calculate-new-version.outputs.failure_reason }}"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `current_version` | Current version string (e.g., `R1-2025.3`) | Yes | - |
| `changes_detected` | Whether changes were detected (`true` or `false`) | Yes | - |
| `version_pattern` | Regex pattern for version matching | No | `^(R[0-9]+-[0-9]+)\.([0-9]+)$` |
| `increment_type` | Type of increment (`patch`, `minor`, `major`) | No | `patch` |

## Outputs

| Output | Description | Example |
|--------|-------------|---------|
| `new_version` | Calculated new version (unchanged if no changes or pattern match failed) | `R1-2025.6` |
| `updated` | Whether version was successfully incremented (`true` or `false`) | `true` |
| `failure_reason` | Error message if version calculation failed (empty if successful) | `Previous version 'invalid' does not match expected format` |

## Behavior

### Version Increment Logic

The action follows this flow:

1. **No changes detected** → Version remains unchanged, `updated=false`
2. **Changes detected + valid version format** → Version incremented, `updated=true`
3. **Changes detected + invalid version format** → Version unchanged, `updated=false`, `failure_reason` set

### FOLIO Version Pattern

The default version pattern follows FOLIO's release convention:
- Format: `R<iteration>-<year>.<patch>`
- Examples:
  - `R1-2025.0` → First iteration of 2025, patch 0
  - `R1-2025.5` → First iteration of 2025, patch 5
  - `R2-2025.0` → Second iteration of 2025, patch 0

### Increment Types

Currently supported:
- **patch** (default): Increments the patch number (e.g., `R1-2025.5` → `R1-2025.6`)

Future support planned for:
- **minor**: Would increment minor version in different schemes
- **major**: Would increment major version in different schemes

### Error Handling

#### Invalid Version Format

If the current version doesn't match the pattern:
- `updated` = `false`
- `new_version` = original version (unchanged)
- `failure_reason` = descriptive error message
- Workflow continues (non-blocking)
- A `::warning::` annotation is created

#### Unsupported Increment Type

If an unsupported increment type is specified:
- `updated` = `false`
- `new_version` = original version (unchanged)
- `failure_reason` = descriptive error message
- A `::warning::` annotation is created

## Test Scenarios

### Test 1: No Changes Detected

```yaml
- name: Test no changes
  uses: folio-org/platform-lsp/.github/actions/calculate-version-increment@master
  with:
    current_version: R1-2025.5
    changes_detected: false

# Expected outputs:
# new_version: R1-2025.5
# updated: false
# failure_reason: ''
```

### Test 2: Changes Detected with Valid Version

```yaml
- name: Test changes with valid version
  uses: folio-org/platform-lsp/.github/actions/calculate-version-increment@master
  with:
    current_version: R1-2025.5
    changes_detected: true

# Expected outputs:
# new_version: R1-2025.6
# updated: true
# failure_reason: ''
```

### Test 3: Changes Detected with Invalid Version

```yaml
- name: Test changes with invalid version
  uses: folio-org/platform-lsp/.github/actions/calculate-version-increment@master
  with:
    current_version: invalid-version
    changes_detected: true

# Expected outputs:
# new_version: invalid-version
# updated: false
# failure_reason: "Previous version 'invalid-version' does not match expected format 'R<iteration>-<year>.<patch>'"
```

### Test 4: Custom Version Pattern

```yaml
- name: Test custom pattern
  uses: folio-org/platform-lsp/.github/actions/calculate-version-increment@master
  with:
    current_version: v2.1.3
    changes_detected: true
    version_pattern: '^v([0-9]+)\.([0-9]+)\.([0-9]+)$'
    increment_type: patch

# Expected outputs (note: current implementation only handles 2-capture-group patterns):
# For full support of 3-capture-group patterns, action would need extension
```

## Requirements

- Bash shell environment
- No external dependencies beyond Bash built-ins

## Implementation Notes

### Regex Pattern Matching

The action uses Bash's `=~` operator for regex matching. Captured groups are accessed via `${BASH_REMATCH[n]}`:
- `BASH_REMATCH[1]` = first capture group (base version)
- `BASH_REMATCH[2]` = second capture group (patch number)

### Safe Defaults

Following FOLIO's fail-closed principle:
- Invalid versions don't block the workflow but are clearly reported
- Unsupported increment types result in warnings
- All failures are logged with `::warning::` annotations

### Extensibility

The action is designed for future extension:
- Custom version patterns via `version_pattern` input
- Additional increment types can be added to the `case` statement
- Support for 3-part semantic versions (major.minor.patch) can be added

## Related Actions

- **fetch-base-file**: Fetches baseline files for comparison
- **generate-platform-diff-report**: Generates diff reports that determine if changes exist
- **compare-components**: Compares component versions to detect changes

## Examples from FOLIO Workflows

### Example 1: Release Update Flow

From `release-update-flow.yml`:

```yaml
jobs:
  update-platform-descriptor:
    steps:
      - name: Compare Components & Applications
        id: compare-components
        # ... comparison logic ...
        # Outputs: previous_version, changes_detected

      - name: Calculate New Version
        id: calculate-new-version
        uses: folio-org/platform-lsp/.github/actions/calculate-version-increment@master
        with:
          current_version: ${{ steps.compare-components.outputs.previous_version }}
          changes_detected: ${{ steps.compare-components.outputs.changes_detected }}

      - name: Apply Descriptor Updates
        if: steps.calculate-new-version.outputs.updated == 'true'
        env:
          NEW_VERSION: ${{ steps.calculate-new-version.outputs.new_version }}
        run: |
          jq --arg version "$NEW_VERSION" '.version = $version' platform-descriptor.json
```

### Example 2: Snapshot Update Flow

Similar usage in snapshot workflows:

```yaml
- name: Determine version increment
  id: version
  uses: folio-org/platform-lsp/.github/actions/calculate-version-increment@master
  with:
    current_version: ${{ steps.read-descriptor.outputs.version }}
    changes_detected: ${{ steps.check-updates.outputs.has_updates }}
```

## Troubleshooting

### Issue: Version Not Incrementing

**Symptom:** `updated=false` even when changes are detected

**Possible Causes:**
1. Version format doesn't match the pattern
2. `changes_detected` input is not exactly `'true'`

**Solution:**
- Check the `failure_reason` output for details
- Verify version matches pattern: `R<iteration>-<year>.<patch>`
- Ensure `changes_detected` is a boolean string `'true'`, not other truthy values

### Issue: Custom Pattern Not Working

**Symptom:** Action fails or doesn't increment with custom pattern

**Possible Causes:**
1. Pattern requires 3+ capture groups but action expects 2
2. Pattern syntax incompatible with Bash regex

**Solution:**
- Use 2-capture-group patterns: `^(base)\.([0-9]+)$`
- Test pattern separately: `[[ "R1-2025.5" =~ ^(R[0-9]+-[0-9]+)\.([0-9]+)$ ]] && echo "${BASH_REMATCH[1]}.${BASH_REMATCH[2]}"`

## Contributing

When extending this action:
1. Maintain backward compatibility with FOLIO's default pattern
2. Add comprehensive test cases for new increment types
3. Update this README with new examples
4. Follow FOLIO's safe shell practices (`set -euo pipefail`, `IFS=$'\n\t'`)

## License

Copyright © 2025 The Open Library Foundation

Licensed under the Apache License, Version 2.0. See LICENSE file for details.

