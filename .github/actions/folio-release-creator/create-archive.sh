#!/bin/bash
set -euo pipefail

# FOLIO Release Artifact Creator - Archive Creation Script
# Creates tar.gz archives with proper naming and validation

echo "📦 Creating archive for variant: $VARIANT"

# Function to ensure required tools are available
ensure_tools() {
    if ! command -v tar &> /dev/null; then
        echo "::error::tar command not found"
        exit 1
    fi

    if ! command -v gzip &> /dev/null; then
        echo "::error::gzip command not found"
        exit 1
    fi

    if ! command -v sha256sum &> /dev/null && ! command -v shasum &> /dev/null; then
        echo "::error::sha256sum or shasum command not found"
        exit 1
    fi
}

# Function to generate archive name
generate_archive_name() {
    local version="$1"
    local variant="$2"

    # Extract platform name from platform-descriptor.json if available
    local platform_name="platform-lsp"
    if [[ -f "platform-descriptor.json" ]]; then
        local desc_name
        desc_name=$(jq -r '.name // "platform-lsp"' platform-descriptor.json 2>/dev/null || echo "platform-lsp")
        # Convert to lowercase and replace spaces with hyphens
        platform_name=$(echo "$desc_name" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g')

        # Fallback if conversion results in empty string
        if [[ -z "$platform_name" ]]; then
            platform_name="platform-lsp"
        fi
    fi

    # Create archive name with variant suffix if not 'complete'
    if [[ "$variant" == "complete" ]]; then
        echo "${platform_name}-${version}.tar.gz"
    else
        echo "${platform_name}-${version}--${variant}.tar.gz"
    fi
}

# Function to create reproducible tar archive
create_reproducible_archive() {
    local source_dir="$1"
    local archive_path="$2"

    echo "📦 Creating reproducible tar.gz archive..."
    echo "  Source: $source_dir"
    echo "  Target: $archive_path"

    # Use reproducible tar options for consistent archives
    local tar_opts=(
        "--create"
        "--gzip"
        "--file" "$archive_path"
        "--directory" "$(dirname "$source_dir")"
        "--sort=name"
        "--mtime=@${SOURCE_DATE_EPOCH:-$(date +%s)}"
        "--owner=0"
        "--group=0"
        "--numeric-owner"
        "--pax-option=exthdr.name=%d/PaxHeaders/%f,delete=atime,delete=ctime"
    )

    # Create the archive
    if tar "${tar_opts[@]}" "$(basename "$source_dir")"; then
        echo "    ✅ Archive created successfully"
    else
        echo "    ❌ Failed to create archive"
        exit 1
    fi

    # Verify the archive
    if tar -tzf "$archive_path" >/dev/null 2>&1; then
        echo "    ✅ Archive integrity verified"
    else
        echo "    ❌ Archive integrity check failed"
        exit 1
    fi
}

# Function to generate checksums
generate_checksums() {
    local archive_path="$1"
    local checksum_file="${archive_path}.sha256"

    echo "🔐 Generating checksums..."

    # Generate SHA256 checksum
    if command -v sha256sum &> /dev/null; then
        sha256sum "$archive_path" > "$checksum_file"
    elif command -v shasum &> /dev/null; then
        shasum -a 256 "$archive_path" > "$checksum_file"
    else
        echo "::error::No checksum utility available"
        exit 1
    fi

    echo "    ✅ SHA256 checksum: $(cut -d' ' -f1 "$checksum_file")"
    echo "    📄 Checksum file: $checksum_file"
}

# Function to validate archive contents
validate_archive() {
    local archive_path="$1"
    local expected_variant="$2"

    echo "🔍 Validating archive contents..."

    # List archive contents
    local content_list
    content_list=$(tar -tzf "$archive_path" | head -20)

    echo "    📋 Archive contents (first 20 items):"
    echo "$content_list" | sed 's/^/      /'

    # Check for required files based on variant
    local required_checks=()

    case "$expected_variant" in
        "minimal")
            required_checks=("platform-descriptor.json" "package.json")
            ;;
        "complete")
            required_checks=("platform-descriptor.json" "package.json" "stripes.config.js")
            ;;
        *)
            required_checks=("platform-descriptor.json" "package.json")
            ;;
    esac

    echo "    🔍 Checking for required files:"
    for required_file in "${required_checks[@]}"; do
        if tar -tzf "$archive_path" | grep -q "/$required_file$\|^[^/]*/$required_file$"; then
            echo "      ✅ Found: $required_file"
        else
            echo "      ❌ Missing: $required_file"
            echo "::error::Required file $required_file not found in archive"
            exit 1
        fi
    done

    # Count total files
    local file_count
    file_count=$(tar -tzf "$archive_path" | wc -l)
    echo "    📊 Total items in archive: $file_count"

    echo "    ✅ Archive validation completed"
}

# Function to create archive metadata
create_archive_metadata() {
    local archive_path="$1"
    local archive_name="$2"
    local metadata_file="$3"

    echo "📄 Creating archive metadata..."

    local archive_size
    archive_size=$(stat -c%s "$archive_path" 2>/dev/null || stat -f%z "$archive_path" 2>/dev/null)

    local checksum
    if [[ -f "${archive_path}.sha256" ]]; then
        checksum=$(cut -d' ' -f1 "${archive_path}.sha256")
    else
        checksum="unknown"
    fi

    cat > "$metadata_file" << EOF
{
  "archive_name": "$archive_name",
  "variant": "$VARIANT",
  "version": "$VERSION",
  "size_bytes": $archive_size,
  "size_human": "$(numfmt --to=iec $archive_size)",
  "sha256": "$checksum",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "created_by": "folio-release-creator",
  "repository": "${GITHUB_REPOSITORY:-unknown}",
  "commit": "${GITHUB_SHA:-unknown}"
}
EOF

    echo "    ✅ Metadata saved to: $metadata_file"
}

# Main archive creation function
create_archive() {
    echo "🚀 Starting archive creation for variant: $VARIANT"

    ensure_tools

    # Get artifact directory from previous step
    local artifact_dir
    if [[ -f "$WORK_DIR/artifact-dir.txt" ]]; then
        artifact_dir=$(cat "$WORK_DIR/artifact-dir.txt")
    else
        echo "::error::Artifact directory not found. Did file collection complete successfully?"
        exit 1
    fi

    if [[ ! -d "$artifact_dir" ]]; then
        echo "::error::Artifact directory does not exist: $artifact_dir"
        exit 1
    fi

    echo "📁 Using artifact directory: $artifact_dir"

    # Generate archive name
    local archive_name
    archive_name=$(generate_archive_name "$VERSION" "$VARIANT")
    local archive_path="$WORK_DIR/$archive_name"

    echo "📦 Archive name: $archive_name"
    echo "📁 Archive path: $archive_path"

    # Set SOURCE_DATE_EPOCH for reproducible builds
    export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(date +%s)}

    # Create the archive
    create_reproducible_archive "$artifact_dir" "$archive_path"

    # Generate checksums
    generate_checksums "$archive_path"

    # Validate archive
    validate_archive "$archive_path" "$VARIANT"

    # Create metadata
    local metadata_file="$WORK_DIR/archive-metadata.json"
    create_archive_metadata "$archive_path" "$archive_name" "$metadata_file"

    # Save archive info for upload step
    echo "$archive_name" > "$WORK_DIR/artifact-name.txt"

    local archive_size
    archive_size=$(stat -c%s "$archive_path" 2>/dev/null || stat -f%z "$archive_path" 2>/dev/null)
    echo "$archive_size" > "$WORK_DIR/artifact-size.txt"

    # Set action outputs
    echo "artifact_name=$archive_name" >> $GITHUB_OUTPUT
    echo "artifact_size=$archive_size" >> $GITHUB_OUTPUT

    # Final summary
    echo ""
    echo "📊 Archive Creation Summary:"
    echo "  📦 Archive: $archive_name"
    echo "  📊 Size: $(numfmt --to=iec $archive_size)"
    echo "  🔐 SHA256: $(cut -d' ' -f1 "${archive_path}.sha256" 2>/dev/null || echo 'unknown')"
    echo "  📁 Location: $archive_path"
    echo "  📄 Metadata: $metadata_file"

    echo ""
    echo "✅ Archive creation completed successfully!"
}

# Main execution
echo "Starting archive creation for FOLIO release artifact..."
echo "Variant: $VARIANT"
echo "Version: $VERSION"
echo "Work Directory: $WORK_DIR"

create_archive

echo "📦 Archive creation phase completed!"
