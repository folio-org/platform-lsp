# Generate Platform Diff Report Action

Generates a collapsed diff and formatted markdown report comparing platform descriptors (eureka-components and applications) between a base branch and head branch. This action consolidates complex inline diff calculation and markdown rendering logic.

## Purpose

This action solves the complex pattern of comparing platform descriptors across branches by:
- Calculating collapsed diffs for eureka-components, required applications, and optional applications
- Identifying version changes for modules present in both descriptors
- Rendering a clean markdown table grouped by component type
- Providing structured JSON output for further processing

## Usage

### Basic Usage

Generate a diff report between base and head descriptors:

```yaml
- name: Generate platform diff report
  id: diff-report
  uses: folio-org/platform-lsp/.github/actions/generate-platform-diff-report@master
  with:
    base_descriptor_path: platform-descriptor.base.json
    head_descriptor_path: platform-descriptor.json
    release_branch: R1-2025
    update_branch: R1-2025-update
    platform_version: R1-2025.1
```

### With Base File Fetch

Combine with fetch-base-file action:

```yaml
- name: Fetch base descriptor
  id: fetch-base
  uses: folio-org/platform-lsp/.github/actions/fetch-base-file@master
  with:
    base_branch: R1-2025
    file_path: platform-descriptor.json
    output_filename: platform-descriptor.base.json

- name: Generate diff report
  id: diff
  uses: folio-org/platform-lsp/.github/actions/generate-platform-diff-report@master
  with:
    base_descriptor_path: ${{ steps.fetch-base.outputs.file_path }}
    head_descriptor_path: platform-descriptor.json
    release_branch: R1-2025
    update_branch: R1-2025-update
    platform_version: ${{ steps.version-calc.outputs.new_version }}

- name: Use report in PR body
  run: |
    gh pr create \
      --title "Update platform" \
      --body "${{ steps.diff.outputs.updates_markdown }}"
```

### Conditional Logic Based on Changes

Only proceed with updates if changes are detected:

```yaml
- name: Generate diff report
  id: diff
  uses: folio-org/platform-lsp/.github/actions/generate-platform-diff-report@master
  with:
    base_descriptor_path: base.json
    head_descriptor_path: head.json
    release_branch: main
    update_branch: feature-branch

- name: Commit changes
  if: steps.diff.outputs.has_changes == 'true'
  run: |
    echo "Found ${{ steps.diff.outputs.updates_cnt }} changes"
    git commit -am "Update platform"
    git push
```

### Use JSON Diff for Processing

Access structured diff data for custom processing:

```yaml
- name: Generate diff report
  id: diff
  uses: folio-org/platform-lsp/.github/actions/generate-platform-diff-report@master
  with:
    base_descriptor_path: base.json
    head_descriptor_path: head.json
    release_branch: R1-2025
    update_branch: R1-2025-update

- name: Process diff JSON
  env:
    DIFF_JSON: ${{ steps.diff.outputs.diff_json }}
  run: |
    echo "$DIFF_JSON" | jq -r '.[] | select(.group == "Eureka Components") | .name'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `base_descriptor_path` | Path to base platform descriptor JSON file | Yes | - |
| `head_descriptor_path` | Path to head platform descriptor JSON file | Yes | - |
| `release_branch` | Base branch name for display in markdown | Yes | - |
| `update_branch` | Head branch name for display in markdown | Yes | - |
| `platform_version` | Platform version for display in markdown | No | `''` |

## Outputs

| Output | Description | Example |
|--------|-------------|---------|
| `updates_markdown` | Formatted markdown report of changes | See [Markdown Format](#markdown-format) |
| `updates_cnt` | Total number of changes detected | `5` |
| `diff_json` | JSON array of all changes | `[{"name":"mod-foo","change":{"old":"1.0","new":"1.1"},"group":"Eureka Components"}]` |
| `has_changes` | Whether any changes were detected | `true` or `false` |

## Markdown Format

The `updates_markdown` output produces a formatted table:

```markdown
### Application & Component Updates

**Base branch:** R1-2025
**Head branch:** R1-2025-update
**Platform version:** R1-2025.1
**Changed entries:** 3

| Name | Old Version | New Version | Group |
| ---- | ----------- | ----------- | ----- |
| mod-inventory | 1.0.0 | 1.1.0 | Eureka Components |
| mod-circulation | 2.0.0 | 2.1.0 | Eureka Components |
| folio_inventory | 3.0.0 | 3.1.0 | Applications (required) |

> This table shows the collapsed diff of `platform-descriptor.json` between base and head branches.
```

When no changes are detected:

```markdown
### Application & Component Updates

_No changes detected between base and head._
```

## JSON Diff Format

The `diff_json` output is a JSON array where each element represents a change:

```json
[
  {
    "name": "mod-inventory",
    "change": {
      "old": "1.0.0",
      "new": "1.1.0"
    },
    "group": "Eureka Components"
  },
  {
    "name": "folio_inventory",
    "change": {
      "old": "3.0.0",
      "new": "3.1.0"
    },
    "group": "Applications (required)"
  }
]
```

Groups can be:
- `Eureka Components`
- `Applications (required)`
- `Applications (optional)`

## Behavior

### Success Path

1. Validates both descriptor files exist
2. Extracts `eureka-components` from both descriptors
3. Extracts `applications.required` from both descriptors
4. Extracts `applications.optional` from both descriptors
5. For each section, calculates collapsed diff (modules present in both with version changes)
6. Combines all diffs into a single JSON array
7. Renders markdown table with changes grouped by section
8. Outputs markdown, JSON, count, and boolean flag

### Diff Calculation Logic

The action uses a "collapsed diff" approach:
- Only includes modules that exist in **both** base and head descriptors
- Only includes modules where the **version has changed**
- Modules added or removed are **not** included (this is intentional for update workflows)

This differs from a full diff and is optimized for release update workflows where you want to see version changes for existing modules.

### Error Handling

- Missing base descriptor → `::error::`, workflow fails
- Missing head descriptor → `::error::`, workflow fails
- Invalid JSON in descriptors → jq parsing error, workflow fails
- Missing sections (e.g., no `eureka-components` field) → jq error, workflow fails

## Requirements

### System Dependencies

- `jq` (JSON processor)
- `bash` 4.0+

### Descriptor Format

Both descriptors must follow the platform descriptor schema:

```json
{
  "version": "R1-2025.0",
  "eureka-components": [
    {"name": "mod-foo", "version": "1.0.0"}
  ],
  "applications": {
    "required": [
      {"name": "app-bar", "version": "2.0.0"}
    ],
    "optional": [
      {"name": "app-baz", "version": "3.0.0"}
    ]
  }
}
```

## Testing

### Manual Testing

Create test descriptors:

```bash
cat > base-test.json <<'EOF'
{
  "version": "R1-2025.0",
  "eureka-components": [
    {"name": "mod-foo", "version": "1.0.0"},
    {"name": "mod-bar", "version": "2.0.0"}
  ],
  "applications": {
    "required": [{"name": "app-baz", "version": "3.0.0"}],
    "optional": []
  }
}
EOF

cat > head-test.json <<'EOF'
{
  "version": "R1-2025.1",
  "eureka-components": [
    {"name": "mod-foo", "version": "1.1.0"},
    {"name": "mod-bar", "version": "2.0.0"}
  ],
  "applications": {
    "required": [{"name": "app-baz", "version": "3.1.0"}],
    "optional": []
  }
}
EOF

# Run script locally
export BASE_DESCRIPTOR=base-test.json
export HEAD_DESCRIPTOR=head-test.json
export RELEASE_BRANCH=R1-2025
export UPDATE_BRANCH=R1-2025-update
export PLATFORM_VERSION=R1-2025.1
export GITHUB_OUTPUT=/tmp/test-output

./.github/actions/generate-platform-diff-report/scripts/generate-diff.sh

# Check output
cat /tmp/test-output
```

Expected output:
- `updates_cnt=2` (mod-foo and app-baz changed, mod-bar unchanged)
- `has_changes=true`
- Markdown table with 2 rows
- JSON array with 2 elements

### Test Scenarios

| Scenario | Base | Head | Expected Result |
|----------|------|------|-----------------|
| No changes | Same versions | Same versions | `has_changes=false`, count=0 |
| All changed | v1.0 | v1.1 | `has_changes=true`, count=N |
| Partial change | Mixed | Some v1.1 | Only changed modules in diff |
| Missing base | - | Exists | Error, workflow fails |
| Invalid JSON | Invalid | Valid | jq error, workflow fails |

## Performance

- Processes descriptors with 100+ modules in <1 second
- Uses in-memory jq operations (no intermediate files)
- Scales linearly with number of modules

## Design Rationale

### Why Collapsed Diff?

The action uses a "collapsed diff" that only shows modules present in both descriptors with version changes. This is intentional for release update workflows where:
- New modules in head are expected (new dependencies)
- Removed modules are rare and handled separately
- Focus is on **version updates** for existing modules

For full diff (additions/removals), use standard `jq` diff or extend this action.

### Why Bash Instead of Python?

- Zero additional dependencies (bash + jq available in all GitHub runners)
- Simple transformations suitable for shell scripts
- Consistent with other FOLIO CI/CD scripts
- Easier to debug and modify inline

### Why Inline jq Instead of External Script?

- The jq query is self-contained and declarative
- Splitting it would reduce readability
- Performance is identical

## Troubleshooting

### "Base descriptor not found" Error

**Cause:** The `base_descriptor_path` doesn't exist.

**Solution:** Ensure you've fetched the base file first using `fetch-base-file` action or that the path is correct.

### "jq: error parsing JSON" Error

**Cause:** One of the descriptors is invalid JSON.

**Solution:** Validate both descriptors:
```bash
jq empty base.json
jq empty head.json
```

### Empty Markdown Table

**Cause:** No modules changed versions between base and head.

**Solution:** This is expected behavior. Check `has_changes` output to conditionally handle this case.

### Unexpected Module Missing from Diff

**Cause:** Module only exists in base or head, not both.

**Solution:** This is expected - collapsed diff only shows version changes for modules present in both descriptors.

## Related Actions

- [`fetch-base-file`](../fetch-base-file/README.md) - Fetch base descriptor for comparison
- [`update-eureka-components`](../update-eureka-components/README.md) - Update eureka components to latest versions
- [`update-applications`](../update-applications/README.md) - Update applications to latest versions

## Contributing

When modifying this action:
1. Test with real platform descriptors
2. Ensure markdown renders correctly in GitHub UI
3. Validate JSON output structure matches schema
4. Update README with new inputs/outputs
5. Add test cases for new scenarios

## License

Apache-2.0

