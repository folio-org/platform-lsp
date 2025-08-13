#!/bin/bash
set -euo pipefail

# FOLIO Release Archive Creator
# Creates a compressed archive of collected platform files

readonly RELEASE_TAG="$1"
readonly CONFIG_PATH="${2:-.github/release-package-config.yml}"
readonly STAGING_DIR="release-staging"

echo "🗜️  Creating release archive for tag: $RELEASE_TAG"

# Early validation
[[ -d "$STAGING_DIR" ]] || {
    echo "::error::Staging directory not found: $STAGING_DIR"
    echo "Make sure collect-files.sh has been run first."
    exit 1
}

# Extract configuration values once
readonly MAX_SIZE_MB=$(yq eval '.settings.max_archive_size_mb' "$CONFIG_PATH" 2>/dev/null || echo "500")
readonly PLATFORM_NAME=$(yq eval '.settings.package_name' "$CONFIG_PATH" 2>/dev/null || echo "platform")

# Add trap for cleanup
cleanup() {
    [[ -d "$STAGING_DIR" ]] && rm -rf "$STAGING_DIR"
    echo "✅ Cleanup completed"
}
trap cleanup EXIT

# Generate clean names for archive
readonly CLEAN_NAME=$(echo "$PLATFORM_NAME" | sed 's/[^a-zA-Z0-9.-]/_/g')
readonly CLEAN_VERSION=$(echo "$RELEASE_TAG" | sed 's/[^a-zA-Z0-9.-]/_/g')
readonly ARCHIVE_NAME="${CLEAN_NAME}-${CLEAN_VERSION}.tar.gz"
readonly ARCHIVE_PATH="$PWD/$ARCHIVE_NAME"

echo "Platform: $PLATFORM_NAME"
echo "Version: $RELEASE_TAG"
echo "Archive: $ARCHIVE_NAME"

# Check staging directory size
echo ""
echo "📏 Checking archive size..."
readonly STAGING_SIZE_KB=$(du -sk "$STAGING_DIR" | cut -f1)
readonly STAGING_SIZE_MB=$((STAGING_SIZE_KB / 1024))

# Display size appropriately
if [[ $STAGING_SIZE_MB -lt 1 ]]; then
    echo "Staging directory size: ${STAGING_SIZE_KB}KB"
else
    echo "Staging directory size: ${STAGING_SIZE_MB}MB"
fi
echo "Maximum allowed size: ${MAX_SIZE_MB}MB"

# Early exit if size exceeds limit
if [[ $STAGING_SIZE_MB -gt $MAX_SIZE_MB ]]; then
    echo "::error::Staging directory size (${STAGING_SIZE_MB}MB) exceeds maximum (${MAX_SIZE_MB}MB)"
    echo "Consider excluding more files or increasing the limit."
    exit 1
fi

# Create the archive
echo ""
echo "🗜️  Creating compressed archive..."

# Create archive with optimal compression
(cd "$STAGING_DIR" && tar -czf "$ARCHIVE_PATH" .) || {
    echo "::error::Failed to create archive"
    exit 1
}

# Verify archive was created and get size
[[ -f "$ARCHIVE_PATH" ]] || {
    echo "::error::Archive was not created: $ARCHIVE_PATH"
    exit 1
}

# Get archive information
readonly ARCHIVE_SIZE=$(stat -f%z "$ARCHIVE_PATH" 2>/dev/null || stat -c%s "$ARCHIVE_PATH")
readonly ARCHIVE_SIZE_MB=$((ARCHIVE_SIZE / 1024 / 1024))
readonly ARCHIVE_SIZE_KB=$((ARCHIVE_SIZE / 1024))

# Display size appropriately
readonly ARCHIVE_SIZE_DISPLAY=$(
    if [[ $ARCHIVE_SIZE_MB -lt 1 ]]; then
        echo "${ARCHIVE_SIZE_KB}KB"
    else
        echo "${ARCHIVE_SIZE_MB}MB"
    fi
)

echo "✅ Archive created successfully"
echo "   Path: $ARCHIVE_PATH"
echo "   Size: ${ARCHIVE_SIZE} bytes (${ARCHIVE_SIZE_DISPLAY})"

# Generate SHA256 checksum
echo ""
echo "🔐 Generating checksum..."
readonly SHA256=$(sha256sum "$ARCHIVE_PATH" | cut -d' ' -f1 2>/dev/null || {
    echo "::warning::No SHA256 utility found, skipping checksum"
    echo ""
})

[[ -n "$SHA256" ]] && echo "SHA256: $SHA256"

# Test archive integrity
echo ""
echo "🧪 Testing archive integrity..."
tar -tzf "$ARCHIVE_PATH" >/dev/null 2>&1 || {
    echo "::error::Archive integrity test failed"
    exit 1
}
echo "✅ Archive integrity test passed"

# List archive contents for verification
echo ""
echo "📋 Archive contents preview (first 20 files):"

# Get file count and preview in parallel
{
    # Get total files count
    readonly total_files=$(tar -tzf "$ARCHIVE_PATH" | wc -l)
    
    # Show preview (disable pipefail temporarily for head)
    set +o pipefail
    tar -tzf "$ARCHIVE_PATH" | head -20 | sed 's/^/  /'
    set -o pipefail
    
    # Show remaining count if needed
    if [[ $total_files -gt 20 ]]; then
        echo "  ... and $((total_files - 20)) more files"
    fi
} 2>/dev/null || {
    echo "  Unable to list archive contents"
    readonly total_files=0
}

# Set outputs for GitHub Actions
echo ""
echo "📤 Setting GitHub Actions outputs..."
{
    echo "archive_path=$ARCHIVE_PATH"
    echo "archive_size=$ARCHIVE_SIZE"
    echo "sha256_checksum=$SHA256"
} >> "$GITHUB_OUTPUT"

# Final summary
echo ""
echo "📊 Archive Creation Summary"
echo "=========================="
echo "Archive: $ARCHIVE_NAME"
echo "Size: ${ARCHIVE_SIZE_DISPLAY}"
echo "Files: ${total_files:-0}"
echo "SHA256: ${SHA256:-N/A}"
echo "✅ Archive creation completed successfully"