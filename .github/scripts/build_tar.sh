#!/usr/bin/env bash
# Build script for creating deterministic release artifact tarball

set -euo pipefail

TAG="${GITHUB_REF_NAME:-unknown}"
ROOT="platform-lsp-${TAG}"

echo "Building release artifact for tag: ${TAG}"

# Set source date epoch from commit timestamp for reproducibility
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
echo "Source date epoch: ${SOURCE_DATE_EPOCH}"

# Create working directory
mkdir -p ".release/${ROOT}"

echo "::group::Copy base files"
# Copy required files
cp -v platform-descriptor.json ".release/${ROOT}/"
cp -v package.json yarn.lock ".release/${ROOT}/"
cp -v stripes.apps.js stripes.config.js stripes.extra.js stripes.plugins.js ".release/${ROOT}/"
echo "::endgroup::"

echo "::group::Create descriptors folder and fetch from registry"
# Create descriptors directory
mkdir -p ".release/${ROOT}/descriptors"

# Read platform-descriptor.json to get application IDs
if [[ ! -f "platform-descriptor.json" ]]; then
    echo "::error::platform-descriptor.json not found"
    exit 1
fi

# Extract application IDs from platform-descriptor.json
app_ids=$(jq -r '.modules[]?.id // empty' platform-descriptor.json)

if [[ -z "${app_ids}" ]]; then
    echo "::warning::No application IDs found in platform-descriptor.json"
else
    echo "Found application IDs:"
    echo "${app_ids}"

    # Fetch each application descriptor from the registry
    for app_id in ${app_ids}; do
        echo "Fetching descriptor for: ${app_id}"

        # Construct URL for the registry
        registry_url="https://far.ci.folio.org/_/proxy/modules/${app_id}"

        # Fetch the descriptor with retry logic
        max_retries=3
        retry_count=0

        while [[ ${retry_count} -lt ${max_retries} ]]; do
            if curl -fsSL "${registry_url}" -o ".release/${ROOT}/descriptors/${app_id}.json"; then
                echo "✓ Successfully fetched ${app_id}.json"
                break
            else
                retry_count=$((retry_count + 1))
                if [[ ${retry_count} -lt ${max_retries} ]]; then
                    echo "::warning::Failed to fetch ${app_id}, retry ${retry_count}/${max_retries}"
                    sleep $((retry_count * 2))
                else
                    echo "::error::Failed to fetch ${app_id} after ${max_retries} retries"
                    exit 1
                fi
            fi
        done
    done
fi

echo "Descriptors folder contents:"
ls -la ".release/${ROOT}/descriptors/"
echo "::endgroup::"

echo "::group::Create deterministic tarball"
# Create deterministic tarball with reproducible flags
tar --sort=name \
    --mtime="@${SOURCE_DATE_EPOCH}" \
    --owner=0 --group=0 --numeric-owner \
    -C .release \
    -czf "platform-lsp-${TAG}.tar.gz" \
    "${ROOT}"

echo "Created tarball: platform-lsp-${TAG}.tar.gz"
ls -lh "platform-lsp-${TAG}.tar.gz"
echo "SHA256: $(sha256sum "platform-lsp-${TAG}.tar.gz" | cut -d' ' -f1)"
echo "::endgroup::"

echo "::notice::Successfully built release artifact: platform-lsp-${TAG}.tar.gz"
