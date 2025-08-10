#!/bin/bash
set -euo pipefail

# FOLIO Release Archive Creator
# Creates a compressed archive of collected platform files

RELEASE_TAG="$1"
CONFIG_PATH="${2:-.github/release-config.yml}"

MAX_SIZE_MB=$(yq eval '.settings.max_archive_size_mb' "$CONFIG_PATH" 2>/dev/null || echo "")

echo "Release tag: $RELEASE_TAG"

echo "🗜️  Creating release archive for tag: $RELEASE_TAG"

STAGING_DIR="release-staging"
if [[ ! -d "$STAGING_DIR" ]]; then
    echo "::error::Staging directory not found: $STAGING_DIR"
    echo "Make sure collect-files.sh has been run first."
    exit 1
fi

# Get platform name and version from config
PLATFORM_NAME=$(yq eval '.settings.package_name' "$CONFIG_PATH" 2>/dev/null || echo "")
PLATFORM_VERSION="$RELEASE_TAG"

# Clean up platform name for filename
CLEAN_NAME=$(echo "$PLATFORM_NAME" | sed 's/[^a-zA-Z0-9.-]/_/g')
CLEAN_VERSION=$(echo "$PLATFORM_VERSION" | sed 's/[^a-zA-Z0-9.-]/_/g')

# Generate archive name
ARCHIVE_NAME="${CLEAN_NAME}-${CLEAN_VERSION}.tar.gz"
ARCHIVE_PATH="$PWD/$ARCHIVE_NAME"

echo "Platform: $PLATFORM_NAME"
echo "Version: $PLATFORM_VERSION"
echo "Archive: $ARCHIVE_NAME"

# Check staging directory size
echo ""
echo "📏 Checking archive size..."
STAGING_SIZE_KB=$(du -sk "$STAGING_DIR" | cut -f1)
STAGING_SIZE_MB=$((STAGING_SIZE_KB / 1024))

echo "Staging directory size: ${STAGING_SIZE_MB}MB"
echo "Maximum allowed size: ${MAX_SIZE_MB}MB"

if [[ $STAGING_SIZE_MB -gt $MAX_SIZE_MB ]]; then
    echo "::error::Staging directory size (${STAGING_SIZE_MB}MB) exceeds maximum (${MAX_SIZE_MB}MB)"
    echo "Consider excluding more files or increasing the limit."
    exit 1
fi

# Create the archive
echo ""
echo "🗜️  Creating compressed archive..."
cd "$STAGING_DIR"

# Create tar.gz with progress indication
tar -czf "$ARCHIVE_PATH" . || {
    echo "::error::Failed to create archive"
    exit 1
}

cd - >/dev/null

# Verify archive was created
if [[ ! -f "$ARCHIVE_PATH" ]]; then
    echo "::error::Archive was not created: $ARCHIVE_PATH"
    exit 1
fi

# Get archive information
ARCHIVE_SIZE=$(stat -f%z "$ARCHIVE_PATH" 2>/dev/null || stat -c%s "$ARCHIVE_PATH" 2>/dev/null)
ARCHIVE_SIZE_MB=$((ARCHIVE_SIZE / 1024 / 1024))

echo "✅ Archive created successfully"
echo "   Path: $ARCHIVE_PATH"
echo "   Size: ${ARCHIVE_SIZE} bytes (${ARCHIVE_SIZE_MB}MB)"

# Generate checksums
echo ""
echo "🔐 Generating checksums..."

# SHA256 checksum
if command -v sha256sum >/dev/null 2>&1; then
    SHA256=$(sha256sum "$ARCHIVE_PATH" | cut -d' ' -f1)
else
    echo "::warning::No SHA256 utility found, skipping checksum"
    SHA256=""
fi

if [[ -n "$SHA256" ]]; then
    echo "SHA256: $SHA256"
fi

# Test archive integrity
echo ""
echo "🧪 Testing archive integrity..."
if tar -tzf "$ARCHIVE_PATH" >/dev/null 2>&1; then
    echo "✅ Archive integrity test passed"
else
    echo "::error::Archive integrity test failed"
    exit 1
fi

# List archive contents for verification
echo ""
echo "📋 Archive contents preview (first 20 files):"

# Temporarily disable pipefail to handle SIGPIPE from head command gracefully
set +o pipefail
tar -tzf "$ARCHIVE_PATH" | head -20 | sed 's/^/  /' || true
total_files=$(tar -tzf "$ARCHIVE_PATH" | wc -l || echo "0")
set -o pipefail

# Convert total_files to number and handle potential whitespace
total_files=$(echo "$total_files" | tr -d '[:space:]')
if [[ "$total_files" =~ ^[0-9]+$ ]] && [[ $total_files -gt 20 ]]; then
    echo "  ... and $((total_files - 20)) more files"
fi

# Set outputs for GitHub Actions
echo ""
echo "📤 Setting GitHub Actions outputs..."
{
  echo "archive_path=$ARCHIVE_PATH"
  echo "archive_size=$ARCHIVE_SIZE"
  echo "sha256_checksum=$SHA256"
} >> "$GITHUB_OUTPUT"


echo ""
echo "📊 Archive Creation Summary"
echo "=========================="
echo "Archive: $ARCHIVE_NAME"
echo "Size: ${ARCHIVE_SIZE_MB}MB"
echo "Files: $total_files"
echo "SHA256: $SHA256"
echo "✅ Archive creation completed successfully"

# Clean up staging directory
echo ""
echo "🧹 Cleaning up staging directory..."
rm -rf "$STAGING_DIR"
echo "✅ Cleanup completed"