# Compare Components Action

Compares current platform descriptor components and applications with updated versions to detect changes using semantic JSON comparison.

## Features

- **Semantic JSON Comparison**: Uses `jq` for accurate comparison, not string matching
- **Input Validation**: Validates all JSON inputs before processing
- **Size Protection**: Warns if outputs exceed GitHub Actions limits
- **Robust Delimiters**: Uses multiple fallback strategies for unique delimiters
- **Pass-through Outputs**: Provides both current and updated values for downstream jobs

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `descriptor_path` | Yes | - | Path to current platform descriptor JSON file |
| `updated_eureka_components` | Yes | - | JSON array of updated eureka-components |
| `updated_applications` | Yes | - | JSON object of updated applications |
| `output_size_limit` | No | `900000` | Maximum output size in bytes (stays under 1MB GitHub limit) |

## Outputs

| Output | Description |
|--------|-------------|
| `changes_detected` | Whether changes were detected (`true`/`false`) |
| `previous_version` | Version from current descriptor |
| `current_eureka_components` | Current eureka-components JSON array |
| `current_applications` | Current applications JSON object |
| `updated_eureka_components` | Updated eureka-components JSON array (pass-through) |
| `updated_applications` | Updated applications JSON object (pass-through) |

## Usage

```yaml
- name: Compare Components
  id: compare
  uses: folio-org/platform-lsp/.github/actions/compare-components@master
  with:
    descriptor_path: platform-descriptor.json
    updated_eureka_components: ${{ steps.update-eureka.outputs.updated-components }}
    updated_applications: ${{ steps.update-apps.outputs.updated-applications }}

- name: Check if changes detected
  if: steps.compare.outputs.changes_detected == 'true'
  run: echo "Changes detected in version ${{ steps.compare.outputs.previous_version }}"
```

## Improvements Over Inline Script

1. **Semantic Comparison**: Uses `jq` equality comparison instead of string matching, avoiding issues with:
   - Whitespace variations
   - Key ordering differences
   - Floating point precision

2. **Validation**: Validates all JSON inputs before processing

3. **Size Protection**: Warns if outputs approach GitHub Actions 1MB limit

4. **Reusability**: Can be used in multiple workflows

5. **Testability**: Can be tested independently with test fixtures

6. **Better Error Handling**: Comprehensive validation with clear error messages

## Error Conditions

- Descriptor file not found or invalid JSON
- Invalid JSON in `updated_eureka_components` input
- Invalid JSON in `updated_applications` input
- Output size exceeds limit (warning only)

## Implementation Notes

- Uses semantic JSON comparison via `jq` equality testing
- Robust delimiter generation with multiple fallbacks: `uuidgen` → `date +%s%N` → `$RANDOM`
- All outputs are validated for size before writing
- Change detection happens independently for components and applications
