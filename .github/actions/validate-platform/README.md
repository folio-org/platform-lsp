# Validate Application Action

A composite GitHub Action for validating FOLIO application descriptors against the FOLIO Application Registry (FAR).

## Description

This action performs comprehensive validation of application descriptors including:
- Module interface integrity checks
- Application dependency validation (conditional)
- Cross-application compatibility verification

**Note**: This action only performs validation. For publishing descriptors to FAR, use the `publish-app-descriptor` action separately.

## Inputs

| Name                                | Description                                                                | Required  | Default               |
|-------------------------------------|----------------------------------------------------------------------------|-----------|-----------------------|
| `app_name`                          | Application name                                                           | **Yes**   | -                     |
| `app_descriptor_file`               | Application descriptor file name                                           | **Yes**   | -                     |
| `app_descriptor_artifact_name`      | Application descriptor artifact name (defaults to `{app_name}-descriptor`) | No        | -                     |
| `platform_descriptor_artifact_name` | Name of the platform descriptor artifact to download                       | No        | `platform-descriptor` |
| `use_platform_descriptor`           | Whether platform descriptor should be used for dependency validation       | No        | `true`                |
| `rely_on_FAR`                       | Whether to rely on FAR for application descriptor dependencies             | No        | `false`               |
| `far_url`                           | FAR API URL base                                                           | **Yes**   | -                     |

## Outputs

| Name                | Description                                        |
|---------------------|----------------------------------------------------|
| `validation_passed` | Whether all validations passed (`true` or `false`) |
| `failure_reason`    | Detailed reason for failure if validation failed   |

## Conditional Validation Logic

The action adapts its validation behavior based on input availability:

1. **Application Descriptor Artifact Not Provided**: Validates descriptor from the repository
2. **Platform Descriptor Artifact Not Provided**: Validates application descriptor only (skips dependency validation)
3. **Neither Descriptor Provided**: Fails validation with a clear error message

This allows for flexible validation scenarios, from simple interface validation to full dependency checks.

## Usage

### Basic Usage with Full Validation

```yaml
steps:
  - name: Validate Application
    uses: folio-org/kitfox-github/.github/actions/validate-application@master
    with:
      app_name: ${{ github.event.repository.name }}
      app_descriptor_file: ${{ needs.generate.outputs.descriptor_file }}
      app_descriptor_artifact_name: ${{ needs.generate.outputs.descriptor_artifact_name }}
      far_url: ${{ vars.FAR_URL }}
```

### Interface Validation Only (No Dependency Check)

When you want to validate only the module interfaces without dependency checks, set `use_platform_descriptor` to `false`:

```yaml
steps:
  - name: Validate Application
    uses: folio-org/kitfox-github/.github/actions/validate-application@master
    with:
      app_name: my-application
      app_descriptor_file: app-descriptor.json
      app_descriptor_artifact_name: my-app-descriptor
      use_platform_descriptor: 'false'
      far_url: ${{ vars.FAR_URL }}
```

### With Custom Platform Descriptor

```yaml
steps:
  - name: Validate with Custom Platform
    uses: folio-org/kitfox-github/.github/actions/validate-application@master
    with:
      app_name: my-application
      app_descriptor_file: app-descriptor.json
      app_descriptor_artifact_name: my-app-descriptor
      platform_descriptor_artifact_name: custom-platform-descriptor
      far_url: ${{ vars.FAR_URL }}
```

### Using FAR for Dependencies

```yaml
steps:
  - name: Validate with FAR Dependencies
    uses: folio-org/kitfox-github/.github/actions/validate-application@master
    with:
      app_name: my-application
      app_descriptor_file: app-descriptor.json
      app_descriptor_artifact_name: my-app-descriptor
      rely_on_FAR: 'true'
      far_url: ${{ vars.FAR_URL }}
```

## Prerequisites

This action expects the following artifacts to be available:
1. **Application descriptor artifact** - Named according to `app_descriptor_artifact_name` (or `{app_name}-descriptor` if not specified)
2. **Platform descriptor artifact** (optional) - Named according to `platform_descriptor_artifact_name` (defaults to `platform-descriptor`)

If the platform descriptor artifact is not provided, only interface validation will be performed.

These artifacts should be uploaded in previous workflow steps using `actions/upload-artifact`.

## Validation Process

1. **Validate Inputs**: Ensures at least one descriptor source is provided
2. **Download Artifacts**: Retrieves application and optionally platform descriptor artifacts
3. **Fetch FAR Descriptors**: If not relying on FAR and platform descriptor is available, fetches all application descriptors from FAR for validation
4. **Module Interface Validation**: Validates module interfaces against FAR API
5. **Dependency Validation** (conditional): Validates application dependencies if platform descriptor is available

## Error Handling

The action will fail if:
- Neither application descriptor artifact nor file is provided
- Required artifacts are not found
- Descriptor validation fails (invalid JSON, missing fields, etc.)
- Module interface validation fails
- Dependency validation fails (when platform descriptor is provided)

All errors are reported through the `failure_reason` output and in the action logs.

## Example Workflow

```yaml
name: Validate Application
on:
  workflow_dispatch:

jobs:
  generate:
    runs-on: ubuntu-latest
    outputs:
      descriptor_file: ${{ steps.generate.outputs.descriptor_file }}
      descriptor_file_name: ${{ steps.generate.outputs.descriptor_file_name }}
    steps:
      - name: Generate Descriptor
        id: generate
        # ... generate application descriptor ...

      - name: Upload Descriptor Artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ steps.generate.outputs.descriptor_file_name }}
          path: ${{ steps.generate.outputs.descriptor_file }}

  validate:
    needs: generate
    runs-on: ubuntu-latest
    steps:
      - name: Validate Application
        id: validate
        uses: folio-org/kitfox-github/.github/actions/validate-application@master
        with:
          app_name: ${{ github.event.repository.name }}
          app_descriptor_file: ${{ needs.generate.outputs.descriptor_file }}
          app_descriptor_artifact_name: ${{ needs.generate.outputs.descriptor_artifact_name }}
          far_url: ${{ vars.FAR_URL }}

      - name: Publish Application Descriptor
        if: steps.validate.outputs.validation_passed == 'true'
        uses: folio-org/kitfox-github/.github/actions/publish-app-descriptor@master
        with:
          descriptor-artifact-name: ${{ needs.generate.outputs.descriptor_artifact_name }}
          descriptor-file-name: ${{ needs.generate.outputs.descriptor_file }}
          far-url: ${{ vars.FAR_URL }}

      - name: Check Results
        if: always()
        run: |
          echo "Validation passed: ${{ steps.validate.outputs.validation_passed }}"
          echo "Failure reason: ${{ steps.validate.outputs.failure_reason }}"
```

## License

This action is part of the FOLIO project and follows the project's licensing terms.
