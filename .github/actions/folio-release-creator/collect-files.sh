#!/bin/bash
set -euo pipefail

# FOLIO Release Artifact Creator - File Collection Script
# Collects all required and optional files for the artifact

echo "📦 Collecting files for variant: $VARIANT"

# Function to ensure yq is available
ensure_yq() {
    if ! command -v yq &> /dev/null; then
        echo "Installing yq for YAML processing..."
        sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
        sudo chmod +x /usr/local/bin/yq
    fi
}

# Function to copy files with pattern matching
copy_files() {
    local file_list="$1"
    local destination="$2"
    local file_type="$3"

    echo "📋 Copying $file_type files:"

    while IFS= read -r file_pattern; do
        if [[ -z "$file_pattern" ]] || [[ "$file_pattern" == "null" ]]; then
            continue
        fi

        echo "  Processing: $file_pattern"

        if [[ "$file_pattern" == *"*"* ]]; then
            # Handle glob patterns
            local matches
            matches=$(find . -maxdepth 2 -name "$file_pattern" -type f 2>/dev/null || true)

            if [[ -n "$matches" ]]; then
                while IFS= read -r match; do
                    if [[ -n "$match" ]]; then
                        local dest_path="$destination/${match#./}"
                        mkdir -p "$(dirname "$dest_path")"
                        cp -p "$match" "$dest_path"
                        echo "    ✅ Copied: $match → ${dest_path#$destination/}"
                    fi
                done <<< "$matches"
            else
                echo "    ⚠️  No matches found for pattern: $file_pattern"
            fi
        elif [[ -f "$file_pattern" ]]; then
            # Handle direct files
            local dest_path="$destination/$file_pattern"
            mkdir -p "$(dirname "$dest_path")"
            cp -p "$file_pattern" "$dest_path"
            echo "    ✅ Copied: $file_pattern"
        elif [[ -d "$file_pattern" ]]; then
            # Handle directories
            local dest_path="$destination/$file_pattern"
            mkdir -p "$dest_path"
            cp -rp "$file_pattern"/* "$dest_path"/ 2>/dev/null || true
            echo "    ✅ Copied directory: $file_pattern"
        else
            if [[ "$file_type" == "required" ]]; then
                echo "    ❌ Required file not found: $file_pattern"
                exit 1
            else
                echo "    ⚠️  Optional file not found: $file_pattern"
            fi
        fi
    done <<< "$file_list"
}

# Function to collect from mgr-applications API
collect_from_mgr_applications() {
    local destination="$1"

    echo "🌐 Collecting application descriptors from mgr-applications API"
    echo "API URL: $MGR_APPLICATIONS_URL"

    # Create mgr-applications directory
    local mgr_dir="$destination/mgr-applications"
    mkdir -p "$mgr_dir"

    # Try to fetch application list
    local api_url="$MGR_APPLICATIONS_URL/mgr-applications/applications"

    echo "  Fetching application list from: $api_url"

    if curl -sf "$api_url" -o "$mgr_dir/applications.json"; then
        echo "    ✅ Successfully fetched applications list"

        # Parse and count applications
        local app_count
        app_count=$(jq length "$mgr_dir/applications.json" 2>/dev/null || echo "0")
        echo "    📊 Found $app_count applications"

        # Optionally fetch individual application details
        if [[ "$app_count" -gt 0 ]]; then
            echo "  Fetching individual application descriptors..."

            local processed=0
            local max_apps=50  # Limit to prevent excessive API calls

            jq -r '.[].id // empty' "$mgr_dir/applications.json" 2>/dev/null | head -n $max_apps | while read -r app_id; do
                if [[ -n "$app_id" ]]; then
                    local app_url="$MGR_APPLICATIONS_URL/mgr-applications/applications/$app_id"
                    if curl -sf "$app_url" -o "$mgr_dir/app-$app_id.json"; then
                        echo "    ✅ Fetched: app-$app_id.json"
                        ((processed++))
                    else
                        echo "    ⚠️  Failed to fetch: app-$app_id.json"
                    fi
                fi
            done

            echo "    📊 Processed $processed application descriptors"
        fi
    else
        echo "    ⚠️  Failed to fetch applications from mgr-applications API"
        echo "    This is not critical for the build, continuing..."

        # Create a placeholder file to indicate the attempt was made
        cat > "$mgr_dir/README.txt" << EOF
MGR-Applications API Collection
==============================

API URL: $MGR_APPLICATIONS_URL
Status: Failed to connect
Time: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

This directory would contain application descriptors fetched from the
mgr-applications API, but the connection failed during build.
EOF
    fi
}

# Function to create manifest file
create_manifest() {
    local destination="$1"

    echo "📄 Creating artifact manifest"

    local manifest_file="$destination/MANIFEST.txt"

    cat > "$manifest_file" << EOF
FOLIO Platform Release Artifact Manifest
========================================

Artifact Details:
- Variant: $VARIANT
- Version: $VERSION
- Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- Builder: GitHub Actions
- Repository: $GITHUB_REPOSITORY
- Commit: $GITHUB_SHA

Configuration:
- Config File: $CONFIG_FILE
- MGR Applications URL: $MGR_APPLICATIONS_URL

Contents:
EOF

    # List all files in the artifact
    echo "" >> "$manifest_file"
    echo "Files included in this artifact:" >> "$manifest_file"
    echo "=================================" >> "$manifest_file"

    find "$destination" -type f -not -name "MANIFEST.txt" | sort | while read -r file; do
        local rel_path="${file#$destination/}"
        local file_size
        file_size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || echo "unknown")
        printf "%-50s %10s bytes\n" "$rel_path" "$file_size" >> "$manifest_file"
    done

    echo "" >> "$manifest_file"
    echo "Total files: $(find "$destination" -type f -not -name "MANIFEST.txt" | wc -l)" >> "$manifest_file"
    echo "Total size: $(du -sh "$destination" | cut -f1)" >> "$manifest_file"

    echo "    ✅ Manifest created: MANIFEST.txt"
}

# Main collection function
collect_platform_files() {
    echo "🚀 Starting file collection for variant: $VARIANT"

    ensure_yq

    # Create destination directory structure
    local artifact_dir="$WORK_DIR/platform-$VARIANT"
    mkdir -p "$artifact_dir"

    echo "📁 Artifact directory: $artifact_dir"

    # Get file lists from configuration
    local required_files
    required_files=$(yq eval ".variants.$VARIANT.required_files[]" "$CONFIG_FILE")

    local optional_files
    optional_files=$(yq eval ".variants.$VARIANT.optional_files[]?" "$CONFIG_FILE" 2>/dev/null || echo "")

    # Copy required files
    echo ""
    copy_files "$required_files" "$artifact_dir" "required"

    # Copy optional files
    if [[ -n "$optional_files" ]] && [[ "$optional_files" != "null" ]]; then
        echo ""
        copy_files "$optional_files" "$artifact_dir" "optional"
    fi

    # Include ModuleDescriptors if configured
    local include_descriptors
    include_descriptors=$(yq eval ".variants.$VARIANT.include_module_descriptors // false" "$CONFIG_FILE")

    if [[ "$include_descriptors" == "true" ]] && [[ -d "ModuleDescriptors" ]]; then
        echo ""
        echo "📋 Including ModuleDescriptors:"
        cp -rp "ModuleDescriptors" "$artifact_dir/"
        local descriptor_count
        descriptor_count=$(find "$artifact_dir/ModuleDescriptors" -name "*.json" -type f | wc -l)
        echo "    ✅ Copied $descriptor_count module descriptors"
    fi

    # Collect from mgr-applications if configured
    local collect_mgr
    collect_mgr=$(yq eval ".variants.$VARIANT.collect_from_mgr_applications // false" "$CONFIG_FILE")

    if [[ "$collect_mgr" == "true" ]]; then
        echo ""
        collect_from_mgr_applications "$artifact_dir"
    fi

    # Create manifest
    echo ""
    create_manifest "$artifact_dir"

    # Report collection summary
    echo ""
    echo "📊 Collection Summary:"
    local total_files
    total_files=$(find "$artifact_dir" -type f | wc -l)
    local total_size
    total_size=$(du -sh "$artifact_dir" | cut -f1)

    echo "  📁 Artifact directory: $artifact_dir"
    echo "  📄 Total files: $total_files"
    echo "  📊 Total size: $total_size"
    echo "  📋 Variant: $VARIANT"
    echo "  🏷️  Version: $VERSION"

    # Save collection info for next step
    echo "$artifact_dir" > "$WORK_DIR/artifact-dir.txt"

    echo ""
    echo "✅ File collection completed successfully!"
}

# Main execution
echo "Starting file collection for FOLIO release artifact..."
echo "Variant: $VARIANT"
echo "Version: $VERSION"
echo "Work Directory: $WORK_DIR"

collect_platform_files

echo "📦 File collection phase completed!"
