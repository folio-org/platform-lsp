# Extract Platform Descriptor Fields

Universal action to extract and validate fields from platform-descriptor.json or any JSON file/content. This action provides a reusable solution for safely extracting multiple fields with type validation and size monitoring.

## Purpose

This action solves the common pattern of extracting specific fields from JSON files in workflows. It provides:
- Extraction of multiple fields in a single operation
- Type validation for extracted fields
- Support for both file-based and content-based input
- Output size monitoring (GitHub Actions limits)
- Both individual field outputs and combined JSON object
- Comprehensive error messages with validation

## Usage

### Basic Usage - Extract from File

Extract multiple fields from a platform descriptor file:

```yaml
- name: Extract descriptor fields
  id: extract
  uses: folio-org/platform-lsp/.github/actions/extract-descriptor-fields@master
  with:
    file-path: platform-descriptor.json
    fields: 'eureka-components,applications'

- name: Use extracted fields
  run: |
    echo "Eureka Components: ${{ steps.extract.outputs.eureka-components }}"
    echo "Applications: ${{ steps.extract.outputs.applications }}"
```

### Advanced Usage - With Type Validation

Extract fields with strict type validation:

```yaml
- name: Extract and validate descriptor fields
  id: extract
  uses: folio-org/platform-lsp/.github/actions/extract-descriptor-fields@master
  with:
    file-path: ${{ env.STATE_FILE }}
    fields: 'eureka-components,applications,version'
    validate-schema: 'true'
    expected-types: '{"eureka-components":"array","applications":"object","version":"string"}'

- name: Process eureka-components
  uses: ./.github/actions/update-eureka-components@master
  with:
    components: ${{ steps.extract.outputs.eureka-components }}

- name: Process applications
  uses: ./.github/actions/update-applications@master
  with:
    applications: ${{ steps.extract.outputs.applications }}
```

### Extract from JSON Content

Extract fields from JSON content already in memory:

```yaml
- name: Fetch file content
  id: fetch
  run: |
    CONTENT=$(jq -c . platform-descriptor.json)
    echo "content=$CONTENT" >> "$GITHUB_OUTPUT"

- name: Extract fields from content
  id: extract
  uses: folio-org/platform-lsp/.github/actions/extract-descriptor-fields@master
  with:
    file-content: ${{ steps.fetch.outputs.content }}
    fields: 'version,name,description'

- name: Use version
  run: echo "Version: ${{ steps.extract.outputs.version }}"
```

### Extract Single Field

Extract just one field from a file:

```yaml
- name: Extract version only
  id: extract-version
  uses: folio-org/platform-lsp/.github/actions/extract-descriptor-fields@master
  with:
    file-path: platform-descriptor.json
    fields: 'version'
    validate-schema: 'false'

- name: Display version
  run: echo "Current version: ${{ steps.extract-version.outputs.version }}"
```

### Use Combined Output

Process all extracted fields as a single JSON object:

```yaml
- name: Extract multiple fields
  id: extract
  uses: folio-org/platform-lsp/.github/actions/extract-descriptor-fields@master
  with:
    file-path: platform-descriptor.json
    fields: 'eureka-components,applications,version,dependencies'

- name: Process all fields at once
  run: |
    echo '${{ steps.extract.outputs.extracted-data }}' | jq '.version'
    echo '${{ steps.extract.outputs.extracted-data }}' | jq '."eureka-components" | length'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `file-path` | Path to descriptor JSON file | No* | `''` |
| `file-content` | JSON content as string (alternative to `file-path`) | No* | `''` |
| `fields` | Comma-separated fields to extract (e.g., `"eureka-components,applications,version"`) | Yes | - |
| `validate-schema` | Validate JSON schema and field types | No | `true` |
| `expected-types` | JSON object mapping field to expected type (e.g., `{"eureka-components":"array"}`) | No | `{}` |

\* **Note:** Either `file-path` or `file-content` must be provided, but not both.

### Input Details

#### `fields`
Comma-separated list of field names to extract from the JSON. Whitespace around field names is trimmed automatically.

**Examples:**
- `"version"`
- `"eureka-components,applications"`
- `"name, version, description"` (spaces are trimmed)

#### `expected-types`
JSON object mapping field names to their expected JSON types. Valid types: `string`, `number`, `boolean`, `array`, `object`, `null`.

**Example:**
```json
{
  "eureka-components": "array",
  "applications": "object",
  "version": "string",
  "dependencies": "object"
}
```

## Outputs

| Output | Description | Example |
|--------|-------------|---------|
| `extracted-data` | JSON object with all extracted fields | `{"eureka-components":[...],"applications":{...}}` |
| `eureka-components` | Extracted eureka-components field (if requested) | `[{"name":"folio-kong","version":"3.9.1"}]` |
| `applications` | Extracted applications field (if requested) | `{"required":[...],"optional":[...]}` |
| `version` | Extracted version field (if requested) | `"R1-2025"` |
| `field-count` | Number of fields successfully extracted | `2` |
| `total-size` | Total size of extracted data in bytes | `4567` |
| `success` | Whether extraction succeeded (`true`/`false`) | `true` |

**Note:** Individual field outputs are dynamically created based on the `fields` input. The action creates an output variable for each requested field using the field name.

## Behavior

### Success Path

1. **Input Validation**
   - Ensures either `file-path` or `file-content` is provided (but not both)
   - Parses comma-separated fields list

2. **JSON Loading**
   - If `file-path`: Validates file exists, is not empty, and contains valid JSON
   - If `file-content`: Validates content is valid JSON

3. **Field Extraction**
   - For each requested field:
     - Validates field exists (if `validate-schema=true`)
     - Extracts field value
     - Validates field type (if `expected-types` provided)
     - Calculates field size
     - Creates individual output variable
     - Adds to combined extracted data object

4. **Size Monitoring**
   - Calculates total size of all extracted fields
   - Warns if approaching GitHub Actions output limit (512KB threshold)

5. **Output Generation**
   - Creates individual output for each field
   - Creates combined `extracted-data` JSON object
   - Provides metadata: `field-count`, `total-size`, `success`

### Error Handling

The action fails with descriptive error messages in these cases:

| Scenario | Error Message | Exit Code |
|----------|---------------|-----------|
| No input provided | `Either 'file-path' or 'file-content' input must be provided` | 1 |
| Both inputs provided | `Only one of 'file-path' or 'file-content' should be provided, not both` | 1 |
| File not found | `File '<path>' is missing or empty` | 1 |
| Invalid JSON | `File is not valid JSON` or `Provided content is not valid JSON` | 1 |
| Field not found | `Field '<name>' does not exist in descriptor` | 1 |
| Null field value | `Failed to extract field '<name>' or field is null` | 1 |
| Type mismatch | `Field '<name>' has type '<actual>' but expected '<expected>'` | 1 |

### Type Validation

When `validate-schema=true` and `expected-types` is provided, the action validates each field's type:

```yaml
# This will fail if eureka-components is not an array
with:
  file-path: platform-descriptor.json
  fields: 'eureka-components'
  expected-types: '{"eureka-components":"array"}'
```

Supported JSON types:
- `string` - Text values
- `number` - Numeric values (integers and floats)
- `boolean` - `true` or `false`
- `array` - JSON arrays
- `object` - JSON objects
- `null` - Null values

## Output Size Monitoring

GitHub Actions has a limit of ~1MB per output variable. This action:
- Calculates the size of each extracted field
- Tracks total size across all fields
- Warns when total size exceeds 512KB (approaching limit)
- Provides size information in notices and outputs

Example output:
```
::notice::✓ Extracted 'eureka-components' (6 items, 342 bytes)
::notice::✓ Extracted 'applications' (1234 bytes)
::warning::Total extracted data size (567890 bytes) approaching GitHub Actions output limit (1MB)
```

## Performance Considerations

### Efficiency
- Reads file once, extracts all fields in a single pass
- More efficient than multiple separate extraction operations
- Ideal when multiple fields are needed from the same file

### Best Practices
1. **Extract related fields together** - Better than multiple action calls
2. **Use `validate-schema=false`** - Skip validation if not needed for performance
3. **Monitor output sizes** - Consider artifacts for very large data
4. **Limit fields** - Only extract what you need

## Integration with Other Actions

### Extract → Update → Compare Pattern

```yaml
- name: Extract current state
  id: extract-current
  uses: folio-org/platform-lsp/.github/actions/extract-descriptor-fields@master
  with:
    file-path: platform-descriptor.json
    fields: 'eureka-components,applications'
    validate-schema: 'true'
    expected-types: '{"eureka-components":"array","applications":"object"}'

- name: Update Eureka Components
  id: update-eureka
  uses: folio-org/platform-lsp/.github/actions/update-eureka-components@master
  with:
    components: ${{ steps.extract-current.outputs.eureka-components }}

- name: Update Applications
  id: update-apps
  uses: folio-org/platform-lsp/.github/actions/update-applications@master
  with:
    applications: ${{ steps.extract-current.outputs.applications }}

- name: Compare for changes
  run: |
    ORIGINAL='${{ steps.extract-current.outputs.eureka-components }}'
    UPDATED='${{ steps.update-eureka.outputs.updated-components }}'
    if [[ "$ORIGINAL" != "$UPDATED" ]]; then
      echo "Changes detected!"
    fi
```

## Comparison with Inline Scripts

### Before (70+ lines of shell script)

```yaml
- name: Read descriptor file
  id: read-descriptor
  run: |
    # 70+ lines of validation, extraction, and output logic
    # Hard to reuse, test, or maintain
```

### After (5 lines)

```yaml
- name: Extract descriptor fields
  id: read-descriptor
  uses: folio-org/platform-lsp/.github/actions/extract-descriptor-fields@master
  with:
    file-path: platform-descriptor.json
    fields: 'eureka-components,applications'
    expected-types: '{"eureka-components":"array","applications":"object"}'
```

**Benefits:**
- ✅ 86% reduction in workflow code
- ✅ Reusable across workflows
- ✅ Consistent validation
- ✅ Better error messages
- ✅ Easier to test and maintain

## Troubleshooting

### "Field does not exist in descriptor"

**Cause:** Field name doesn't match JSON structure or is misspelled.

**Solution:** Check field names match JSON keys exactly (case-sensitive):
```bash
# Verify field exists
jq 'keys' platform-descriptor.json
```

### "Type mismatch" error

**Cause:** Field type doesn't match `expected-types` specification.

**Solution:** Check actual field type:
```bash
# Check field type
jq '.fieldname | type' platform-descriptor.json
```

### "Output size approaching limits"

**Cause:** Extracted data exceeds 512KB.

**Solution:**
- Extract fewer fields
- Split into multiple action calls
- Use artifacts for large data transfers

### "Both inputs provided" error

**Cause:** Specified both `file-path` and `file-content`.

**Solution:** Use only one input method.

## Examples

### Real-World: Platform Update Workflow

```yaml
jobs:
  update-platform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Extract descriptor fields
        id: extract
        uses: folio-org/platform-lsp/.github/actions/extract-descriptor-fields@master
        with:
          file-path: platform-descriptor.json
          fields: 'eureka-components,applications,version'
          validate-schema: 'true'
          expected-types: |
            {
              "eureka-components": "array",
              "applications": "object",
              "version": "string"
            }

      - name: Update components
        id: update-components
        uses: folio-org/platform-lsp/.github/actions/update-eureka-components@master
        with:
          components: ${{ steps.extract.outputs.eureka-components }}

      - name: Calculate new version
        run: |
          CURRENT="${{ steps.extract.outputs.version }}"
          echo "Current version: $CURRENT"
          # Version calculation logic...
```

## See Also

- [fetch-base-file](../fetch-base-file/README.md) - Fetch files from base branches
- [update-eureka-components](../update-eureka-components/README.md) - Update Eureka components
- [update-applications](../update-applications/README.md) - Update applications
- [GitHub Actions: Complex Inputs](https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#inputs)
