#!/bin/bash
set -euo pipefail

# FOLIO Release Files Collector
# Collects all required and optional files for the release archive

CONFIG_PATH="${1:-.github/release-config.yml}"

echo "📦 Collecting platform files using config: $CONFIG_PATH"

if [[ ! -f "$CONFIG_PATH" ]]; then
    echo "::error::Configuration file not found: $CONFIG_PATH"
    exit 1
fi

# Create staging directory for files
STAGING_DIR="release-staging"
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

echo "Created staging directory: $STAGING_DIR"

# Function to copy files matching pattern
copy_files() {
    local pattern="$1"
    local file_type="$2"

    echo "  Processing $file_type: $pattern"

    if [[ "$pattern" == *"*"* ]]; then
        # Handle glob patterns
        if [[ "$pattern" == *"/"* ]]; then
            # Directory with glob (e.g., "stripes.*.js")
            dir=$(dirname "$pattern")
            filename=$(basename "$pattern")

            if [[ -d "$dir" ]]; then
                find "$dir" -name "$filename" -type f | while read -r file; do
                    target_dir="$STAGING_DIR/$(dirname "$file")"
                    mkdir -p "$target_dir"
                    cp "$file" "$target_dir/"
                    echo "    ✅ Copied: $file"
                done
            fi
        else
            # Simple glob in current directory
            find . -maxdepth 1 -name "$pattern" -type f | while read -r file; do
                cp "$file" "$STAGING_DIR/"
                echo "    ✅ Copied: $file"
            done
        fi
    else
        # Direct file or directory
        if [[ -f "$pattern" ]]; then
            target_dir="$STAGING_DIR/$(dirname "$pattern")"
            mkdir -p "$target_dir"
            cp "$pattern" "$target_dir/"
            echo "    ✅ Copied file: $pattern"
        elif [[ -d "$pattern" ]]; then
            target_dir="$STAGING_DIR/$pattern"
            mkdir -p "$(dirname "$target_dir")"
            cp -r "$pattern" "$target_dir"
            echo "    ✅ Copied directory: $pattern"
        else
            if [[ "$file_type" == "required" ]]; then
                echo "    ❌ Required file not found: $pattern"
                return 1
            else
                echo "    ⚠️  Optional file not found: $pattern"
            fi
        fi
    fi
}

# Extract file lists from config
REQUIRED_FILES=$(yq eval '.required_files[]' "$CONFIG_PATH" 2>/dev/null || echo "")
OPTIONAL_FILES=$(yq eval '.optional_files[]' "$CONFIG_PATH" 2>/dev/null || echo "")
EXCLUDE_PATTERNS=$(yq eval '.exclude_patterns[]' "$CONFIG_PATH" 2>/dev/null || echo "")

echo ""
echo "📋 Processing required files..."
while IFS= read -r file_pattern; do
    [[ -z "$file_pattern" ]] && continue
    copy_files "$file_pattern" "required"
done <<< "$REQUIRED_FILES"

echo ""
echo "📋 Processing optional files..."
while IFS= read -r file_pattern; do
    [[ -z "$file_pattern" ]] && continue
    copy_files "$file_pattern" "optional"
done <<< "$OPTIONAL_FILES"

## Copy application descriptors if they exist
#if [[ -d "application-descriptors" ]]; then
#    echo ""
#    echo "📋 Copying application descriptors..."
#    cp -r application-descriptors "$STAGING_DIR/"
#    echo "    ✅ Copied application-descriptors/ directory"
#fi

# Remove excluded files
if [[ -n "$EXCLUDE_PATTERNS" ]]; then
    echo ""
    echo "🧹 Removing excluded files..."
    while IFS= read -r pattern; do
        [[ -z "$pattern" ]] && continue
        echo "  Excluding pattern: $pattern"

        find "$STAGING_DIR" -name "$pattern" -type f -delete 2>/dev/null || true
        find "$STAGING_DIR" -name "$pattern" -type d -exec rm -rf {} + 2>/dev/null || true
    done <<< "$EXCLUDE_PATTERNS"
fi

# Create file manifest
echo ""
echo "📋 Creating file manifest..."
MANIFEST_FILE="$STAGING_DIR/MANIFEST.txt"
echo "# FOLIO Platform Release Manifest" > "$MANIFEST_FILE"
echo "# Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$MANIFEST_FILE"
echo "# Configuration: $CONFIG_PATH" >> "$MANIFEST_FILE"
echo "" >> "$MANIFEST_FILE"

echo "## Included Files" >> "$MANIFEST_FILE"
find "$STAGING_DIR" -type f | sed "s|^$STAGING_DIR/||" | sort >> "$MANIFEST_FILE"

echo ""
echo "📊 Collection Summary"
echo "===================="
file_count=$(find "$STAGING_DIR" -type f | wc -l)
dir_count=$(find "$STAGING_DIR" -type d | wc -l)
total_size=$(du -sh "$STAGING_DIR" | cut -f1)

echo "Files collected: $file_count"
echo "Directories: $dir_count"
echo "Total size: $total_size"
echo "Staging directory: $STAGING_DIR"
echo "✅ File collection completed successfully"
