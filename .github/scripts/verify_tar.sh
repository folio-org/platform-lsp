#!/usr/bin/env bash
# Verification script for release artifact tarball

set -euo pipefail

TAG="${GITHUB_REF_NAME:-unknown}"
ARCHIVE="platform-lsp-${TAG}.tar.gz"

echo "Verifying release artifact: ${ARCHIVE}"

if [[ ! -f "${ARCHIVE}" ]]; then
    echo "::error::Archive ${ARCHIVE} not found"
    exit 1
fi

echo "::group::List archive contents"
# List and store tarball contents
tar -tzf "${ARCHIVE}" | tee /tmp/manifest.txt
echo "::endgroup::"

echo "::group::Verify required files"
# Define required files/directories
required=(
    "platform-lsp-${TAG}/platform-descriptor.json"
    "platform-lsp-${TAG}/descriptors/"
    "platform-lsp-${TAG}/package.json"
    "platform-lsp-${TAG}/yarn.lock"
    "platform-lsp-${TAG}/stripes.apps.js"
    "platform-lsp-${TAG}/stripes.config.js"
    "platform-lsp-${TAG}/stripes.extra.js"
    "platform-lsp-${TAG}/stripes.plugins.js"
)

echo "Checking required files:"
missing_files=0
for path in "${required[@]}"; do
    if grep -q "^${path}" /tmp/manifest.txt; then
        echo "✓ ${path}"
    else
        echo "✗ Missing: ${path}"
        missing_files=$((missing_files + 1))
    fi
done

if [[ ${missing_files} -gt 0 ]]; then
    echo "::error::${missing_files} required files are missing"
    exit 1
fi
echo "::endgroup::"

echo "::group::Verify no unexpected top-level files"
# Extract top-level entries and verify against allowlist
grep "^platform-lsp-${TAG}/" /tmp/manifest.txt | \
    sed "s#^platform-lsp-${TAG}/##" | \
    cut -d/ -f1 | \
    sort -u > /tmp/top.txt

# Define allowed top-level entries
allowed_top_level=(
    "platform-descriptor.json"
    "descriptors"
    "package.json"
    "yarn.lock"
    "stripes.apps.js"
    "stripes.config.js"
    "stripes.extra.js"
    "stripes.plugins.js"
)

echo "Allowed top-level entries:"
printf "%s\n" "${allowed_top_level[@]}" | sort -u > /tmp/allowed.txt
cat /tmp/allowed.txt

echo "Actual top-level entries:"
cat /tmp/top.txt

# Check for unexpected entries
unexpected_count=0
while IFS= read -r entry; do
    if ! grep -q "^${entry}$" /tmp/allowed.txt; then
        echo "::error::Unexpected top-level entry: ${entry}"
        unexpected_count=$((unexpected_count + 1))
    fi
done < /tmp/top.txt

if [[ ${unexpected_count} -gt 0 ]]; then
    echo "::error::${unexpected_count} unexpected top-level entries found"
    exit 1
fi
echo "::endgroup::"

echo "::group::Verify descriptors content"
# Check that descriptors directory contains JSON files
descriptor_files=$(grep "^platform-lsp-${TAG}/descriptors/.*\.json$" /tmp/manifest.txt | wc -l)
echo "Found ${descriptor_files} descriptor files"

if [[ ${descriptor_files} -eq 0 ]]; then
    echo "::warning::No descriptor JSON files found in descriptors/ directory"
else
    echo "✓ Descriptors directory contains ${descriptor_files} JSON files"
fi
echo "::endgroup::"

echo "::group::Verify archive structure"
# Verify the archive has exactly one top-level directory
top_level_count=$(tar -tzf "${ARCHIVE}" | cut -d/ -f1 | sort -u | wc -l)
if [[ ${top_level_count} -ne 1 ]]; then
    echo "::error::Archive should contain exactly one top-level directory, found ${top_level_count}"
    exit 1
fi

# Verify the top-level directory name
expected_root="platform-lsp-${TAG}"
actual_root=$(tar -tzf "${ARCHIVE}" | head -1 | cut -d/ -f1)
if [[ "${actual_root}" != "${expected_root}" ]]; then
    echo "::error::Expected root directory '${expected_root}', found '${actual_root}'"
    exit 1
fi

echo "✓ Archive structure is correct with root: ${expected_root}"
echo "::endgroup::"

echo "::group::Final summary"
total_files=$(wc -l < /tmp/manifest.txt)
archive_size=$(du -h "${ARCHIVE}" | cut -f1)
sha256=$(sha256sum "${ARCHIVE}" | cut -d' ' -f1)

echo "Verification complete:"
echo "- Archive: ${ARCHIVE}"
echo "- Size: ${archive_size}"
echo "- Total files: ${total_files}"
echo "- Required files: ${#required[@]} (all present)"
echo "- Descriptors: ${descriptor_files} JSON files"
echo "- SHA256: ${sha256}"
echo "::endgroup::"

echo "::notice::Archive verification passed successfully"
