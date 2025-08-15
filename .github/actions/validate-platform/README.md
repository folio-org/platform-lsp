# Validate Platform Action

A composite GitHub Action that validates a FOLIO platform descriptor by:
- Ensuring the downloaded platform descriptor artifact exists and contains an `.applications` section
- Fetching each listed application descriptor from FAR
- Performing dependency integrity validation against FAR

## Description

This action is designed for platform-level validation. It consumes a previously uploaded platform descriptor artifact, downloads every application descriptor referenced (required and optional), and submits them to FAR's `validate-descriptors` endpoint. It fails closed on any missing artifact, malformed JSON, fetch failure, or dependency integrity issue.

## Inputs

| Name | Description | Required | Default |
|------|-------------|----------|---------|
| `platform_descriptor_artifact_name` | Name of the platform descriptor artifact to download | No       | `platform-descriptor` |
| `far_url` | Base FAR API URL (the action appends `/applications`) | No       | `https://far.ci.folio.org` |

## Outputs

| Name | Description |
|------|-------------|
| `validation_passed` | `true` if dependency validation succeeded, otherwise `false` |
| `failure_reason` | Populated with a human-readable error if validation failed |
| `application_count` | Number of applications (required + optional) discovered in the platform descriptor |

## Artifact Expectations

Upload the platform descriptor artifact in a prior step using `actions/upload-artifact@v4` with a directory containing `platform-descriptor.json` (or the name matching the artifact configured). The JSON must have:

```json
{
  "applications": {
    "required": [ { "name": "app-a", "version": "1.0.0" } ],
    "optional": [ { "name": "app-b", "version": "2.3.1" } ]
  }
}
```

`required` and `optional` arrays are both processed; empty or missing arrays are tolerated.

## Validation Steps

1. Download platform descriptor artifact.
2. Confirm file exists and is non-empty.
3. Verify `.applications` key exists.
4. Extract application list (required + optional) and count.
5. Fetch each application descriptor from FAR (`GET /applications/<name>-<version>?full=true`).
6. Submit all fetched descriptors to FAR (`POST /applications/validate-descriptors`).
7. Emit outputs / failure reason.

## Error Handling

The action stops immediately on:
- Missing or empty artifact
- Missing `.applications` key
- Failure to fetch any application descriptor (network or 4xx/5xx)
- Non-2xx response from validation endpoint

Errors are annotated with `::error::` and the first failure reason is exposed via `failure_reason` output.

## Usage Example

```yaml
jobs:
  validate-platform:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download Platform Descriptor Artifact
        # Normally produced in a previous workflow; shown here for completeness
        uses: actions/download-artifact@v4
        with:
          name: platform-descriptor
          path: /tmp/platform-descriptor

      - name: Validate Platform Descriptor
        id: validate
        uses: folio-org/platform-lsp/.github/actions/validate-platform@master
        with:
          far_url: ${{ vars.FAR_URL }}

      - name: Report Results
        if: always()
        run: |
          echo "Validation passed: ${{ steps.validate.outputs.validation_passed }}"
          echo "Failure reason: ${{ steps.validate.outputs.failure_reason }}"
          echo "Application count: ${{ steps.validate.outputs.application_count }}"
```

## Reuse Pattern (Workflow Call)

To integrate with a reusable workflow, expose outputs downstream:

```yaml
jobs:
  platform-validate:
    uses: folio-org/platform-lsp/.github/workflows/validate-platform.yml@master
    with:
      far_url: ${{ vars.FAR_URL }}
```

(Adjust if you create a reusable workflow wrapper.)

## Future Enhancements (Optional)

| Enhancement | Rationale |
|-------------|-----------|
| Retry logic for descriptor fetches | Improve resilience to transient FAR/network errors |
| Concurrency for fetches | Speed up large platform descriptor validations |
| Dry-run mode | Allow schema checks without FAR calls |
| Failed apps list output | Provide granular diagnostics |

## License

This action is part of the FOLIO project and follows the project's licensing terms.
