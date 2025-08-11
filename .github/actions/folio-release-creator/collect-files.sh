#!/bin/bash
set -euo pipefail

# FOLIO Release Files Collector
# Collects all required and optional files for the release archive

readonly CONFIG_PATH="${1:-.github/release-config.yml}"
readonly STAGING_DIR="release-staging"

echo "📦 Collecting platform files using config: $CONFIG_PATH"

# Early exit if config doesn't exist
[[ -f "$CONFIG_PATH" ]] || {
    echo "::error::Configuration file not found: $CONFIG_PATH"
    exit 1
}

# Create staging directory 
echo "Creating staging directory: $STAGING_DIR"
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

# Function to copy files matching pattern
copy_files() {
    local pattern="$1"
    local file_type="$2"
    local copied_count=0

    echo "  Processing $file_type: $pattern"

    if [[ "$pattern" == *"*"* ]]; then
        # Handle glob patterns
        local files_found=()
        if [[ "$pattern" == *"/"* ]]; then
            # Directory with glob (e.g., "stripes.*.js")
            local dir=$(dirname "$pattern")
            local filename=$(basename "$pattern")
            
            if [[ -d "$dir" ]]; then
                readarray -t files_found < <(find "$dir" -name "$filename" -type f 2>/dev/null || true)
            fi
        else
            # Simple glob in current directory
            readarray -t files_found < <(find . -maxdepth 1 -name "$pattern" -type f 2>/dev/null || true)
        fi
        
        # Copy found files
        for file in "${files_found[@]}"; do
            local target_dir="$STAGING_DIR/$(dirname "$file")"
            mkdir -p "$target_dir"
            cp "$file" "$target_dir/"
            echo "    ✅ Copied: $file"
            ((copied_count++))
        done
        
        if [[ $copied_count -eq 0 && "$file_type" == "required" ]]; then
            echo "    ❌ Required pattern not found: $pattern"
            return 1
        elif [[ $copied_count -eq 0 ]]; then
            echo "    ⚠️  Optional pattern not found: $pattern"
        fi
    else
        # Direct file or directory
        if [[ -f "$pattern" ]]; then
            local target_dir="$STAGING_DIR/$(dirname "$pattern")"
            mkdir -p "$target_dir"
            cp "$pattern" "$target_dir/"
            echo "    ✅ Copied file: $pattern"
            copied_count=1
        elif [[ -d "$pattern" ]]; then
            local target_dir="$STAGING_DIR/$pattern"
            mkdir -p "$(dirname "$target_dir")"
            cp -r "$pattern" "$target_dir"
            echo "    ✅ Copied directory: $pattern"
            copied_count=1
        else
            if [[ "$file_type" == "required" ]]; then
                echo "    ❌ Required file not found: $pattern"
                return 1
            else
                echo "    ⚠️  Optional file not found: $pattern"
            fi
        fi
    fi
    
    return 0
}

# Extract file lists from config once
readonly REQUIRED_FILES=$(yq eval '.required_files[]' "$CONFIG_PATH" 2>/dev/null || echo "")
readonly OPTIONAL_FILES=$(yq eval '.optional_files[]' "$CONFIG_PATH" 2>/dev/null || echo "")
readonly EXCLUDE_PATTERNS=$(yq eval '.exclude_patterns[]' "$CONFIG_PATH" 2>/dev/null || echo "")

# Process required files
echo ""
echo "📋 Processing required files..."
if [[ -n "$REQUIRED_FILES" ]]; then
    while IFS= read -r file_pattern; do
        [[ -n "$file_pattern" ]] && copy_files "$file_pattern" "required"
    done <<< "$REQUIRED_FILES"
else
    echo "  No required files specified"
fi

# Process optional files
echo ""
echo "📋 Processing optional files..."
if [[ -n "$OPTIONAL_FILES" ]]; then
    while IFS= read -r file_pattern; do
        [[ -n "$file_pattern" ]] && copy_files "$file_pattern" "optional"
    done <<< "$OPTIONAL_FILES"
else
    echo "  No optional files specified"
fi

## Copy application descriptors if they exist
#if [[ -d "application-descriptors" ]]; then
#    echo ""
#    echo "📋 Copying application descriptors..."
#    cp -r application-descriptors "$STAGING_DIR/"
#    echo "    ✅ Copied application-descriptors/ directory"
#fi

# Remove excluded files efficiently
if [[ -n "$EXCLUDE_PATTERNS" ]]; then
    echo ""
    echo "🧹 Removing excluded files..."
    
    # Build find command for all patterns at once
    find_args=()
    while IFS= read -r pattern; do
        [[ -n "$pattern" ]] && {
            echo "  Excluding pattern: $pattern"
            find_args+=(-name "$pattern" -o)
        }
    done <<< "$EXCLUDE_PATTERNS"
    
    # Remove the last -o if we have patterns
    if [[ ${#find_args[@]} -gt 0 ]]; then
        unset 'find_args[-1]'  # Remove last -o
        # Execute single find command for all patterns
        find "$STAGING_DIR" \( "${find_args[@]}" \) \( -type f -delete -o -type d -exec rm -rf {} + \) 2>/dev/null || true
    fi
fi

# Create file manifest
echo ""
echo "📋 Creating file manifest..."
readonly MANIFEST_FILE="$STAGING_DIR/MANIFEST.txt"

# Generate manifest in single operation
{
    echo "# FOLIO Platform Release Manifest"
    echo "# Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo "# Configuration: $CONFIG_PATH"
    echo ""
    echo "## Included Files"
    find "$STAGING_DIR" -type f -not -name "MANIFEST.txt" | sed "s|^$STAGING_DIR/||" | sort
} > "$MANIFEST_FILE"

# Generate summary efficiently
echo ""
echo "📊 Collection Summary"
echo "===================="

# Get counts in single operations
readonly file_count=$(find "$STAGING_DIR" -type f | wc -l)
readonly dir_count=$(find "$STAGING_DIR" -type d | wc -l)
readonly total_size=$(du -sh "$STAGING_DIR" | cut -f1)

echo "Files collected: $file_count"
echo "Directories: $dir_count"
echo "Total size: $total_size"
echo "Staging directory: $STAGING_DIR"
echo "✅ File collection completed successfully"
