#!/bin/bash
set -euo pipefail

# FOLIO Release Artifact Creator - File Validation Script
# Validates that all required files exist before proceeding with artifact creation

echo "🔍 Validating required files for variant: $VARIANT"

# Function to check if yq is available, install if needed
ensure_yq() {
    if ! command -v yq &> /dev/null; then
        echo "Installing yq for YAML processing..."
        sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
        sudo chmod +x /usr/local/bin/yq
    fi
}

# Function to expand glob patterns safely
expand_pattern() {
    local pattern="$1"
    if [[ "$pattern" == *"*"* ]]; then
        # Use find for glob patterns
        find . -maxdepth 2 -name "$pattern" -type f 2>/dev/null || true
    else
        # Direct file check
        if [[ -f "$pattern" ]]; then
            echo "$pattern"
        fi
    fi
}

# Main validation function
validate_files() {
    local variant="$1"
    local config_file="$2"

    ensure_yq

    echo "📋 Using configuration file: $config_file"

    # Check if variant exists in config
    if ! yq eval ".variants | has(\"$variant\")" "$config_file" | grep -q "true"; then
        echo "::error::Variant '$variant' not found in configuration file $config_file"
        echo "Available variants:"
        yq eval '.variants | keys | .[]' "$config_file"
        exit 1
    fi

    # Get required files for this variant
    local required_files
    required_files=$(yq eval ".variants.$variant.required_files[]" "$config_file")

    echo "✅ Checking required files for variant '$variant':"

    local missing_files=()
    local found_files=()

    while IFS= read -r file_pattern; do
        if [[ -z "$file_pattern" ]] || [[ "$file_pattern" == "null" ]]; then
            continue
        fi

        echo "  Checking: $file_pattern"

        # Expand the pattern to actual files
        local matches
        matches=$(expand_pattern "$file_pattern")

        if [[ -z "$matches" ]]; then
            missing_files+=("$file_pattern")
            echo "    ❌ Not found: $file_pattern"
        else
            found_files+=("$file_pattern")
            echo "    ✅ Found: $file_pattern"
            # Show actual matched files for patterns
            if [[ "$file_pattern" == *"*"* ]]; then
                while IFS= read -r match; do
                    if [[ -n "$match" ]]; then
                        echo "      → $match"
                    fi
                done <<< "$matches"
            fi
        fi
    done <<< "$required_files"

    # Report results
    echo ""
    echo "📊 Validation Summary:"
    echo "  ✅ Found: ${#found_files[@]} required file(s)"
    echo "  ❌ Missing: ${#missing_files[@]} required file(s)"

    if [[ ${#missing_files[@]} -gt 0 ]]; then
        echo ""
        echo "::error::Missing required files for variant '$variant':"
        for missing_file in "${missing_files[@]}"; do
            echo "::error::  - $missing_file"
        done
        echo ""
        echo "Please ensure all required files are present before creating a release."
        echo "Check the configuration in $config_file for the exact requirements."
        exit 1
    fi

    echo ""
    echo "✅ All required files validated successfully!"

    # Optional: Check for optional files and warn if missing
    local optional_files
    optional_files=$(yq eval ".variants.$variant.optional_files[]?" "$config_file" 2>/dev/null || echo "")

    if [[ -n "$optional_files" ]]; then
        echo ""
        echo "🔍 Checking optional files:"
        while IFS= read -r file_pattern; do
            if [[ -z "$file_pattern" ]] || [[ "$file_pattern" == "null" ]]; then
                continue
            fi

            local matches
            matches=$(expand_pattern "$file_pattern")

            if [[ -z "$matches" ]]; then
                echo "  ⚠️  Optional file not found: $file_pattern"
            else
                echo "  ✅ Optional file found: $file_pattern"
            fi
        done <<< "$optional_files"
    fi
}

# Special validation for FOLIO-specific files
validate_folio_structure() {
    echo ""
    echo "🏛️  Validating FOLIO-specific structure:"

    # Check platform-descriptor.json structure
    if [[ -f "platform-descriptor.json" ]]; then
        echo "  ✅ platform-descriptor.json exists"

        # Validate JSON structure
        if jq empty platform-descriptor.json 2>/dev/null; then
            echo "    ✅ Valid JSON format"

            # Check required fields
            local required_fields=("name" "version" "description")
            for field in "${required_fields[@]}"; do
                if jq -e ".$field" platform-descriptor.json >/dev/null 2>&1; then
                    local value
                    value=$(jq -r ".$field" platform-descriptor.json)
                    echo "    ✅ $field: $value"
                else
                    echo "    ❌ Missing required field: $field"
                    exit 1
                fi
            done
        else
            echo "    ❌ Invalid JSON format"
            exit 1
        fi
    fi

    # Check package.json
    if [[ -f "package.json" ]]; then
        echo "  ✅ package.json exists"
        if jq empty package.json 2>/dev/null; then
            local pkg_name
            pkg_name=$(jq -r '.name // "unknown"' package.json)
            local pkg_version
            pkg_version=$(jq -r '.version // "unknown"' package.json)
            echo "    ✅ Package: $pkg_name@$pkg_version"
        else
            echo "    ❌ Invalid JSON format in package.json"
            exit 1
        fi
    fi

    # Check for ModuleDescriptors if needed
    local include_descriptors
    include_descriptors=$(yq eval ".variants.$VARIANT.include_module_descriptors // false" "$CONFIG_FILE")

    if [[ "$include_descriptors" == "true" ]]; then
        if [[ -d "ModuleDescriptors" ]]; then
            local descriptor_count
            descriptor_count=$(find ModuleDescriptors -name "*.json" -type f | wc -l)
            echo "  ✅ ModuleDescriptors directory found with $descriptor_count JSON files"
        else
            echo "  ⚠️  ModuleDescriptors directory not found (required for this variant)"
            echo "::warning::ModuleDescriptors directory not found but required for variant $VARIANT"
        fi
    fi
}

# Main execution
echo "Starting file validation for FOLIO release artifact creation..."
echo "Variant: $VARIANT"
echo "Config: $CONFIG_FILE"

validate_files "$VARIANT" "$CONFIG_FILE"
validate_folio_structure

echo ""
echo "✅ File validation completed successfully!"
echo "Ready to proceed with artifact creation."
