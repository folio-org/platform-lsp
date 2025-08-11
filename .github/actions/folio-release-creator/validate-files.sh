#!/bin/bash
set -euo pipefail

# FOLIO Release Files Validator
# Validates that all required files exist according to the configuration

readonly CONFIG_PATH="${1:-.github/release-config.yml}"

echo "🔍 Validating required files using config: $CONFIG_PATH"

# Early exit if config doesn't exist
[[ -f "$CONFIG_PATH" ]] || {
    echo "::error::Configuration file not found: $CONFIG_PATH"
    exit 1
}

# Extract required files once
readonly REQUIRED_FILES=$(yq eval '.required_files[]' "$CONFIG_PATH" 2>/dev/null || echo "")

if [[ -z "$REQUIRED_FILES" ]]; then
    echo "::warning::No required files specified in configuration"
    exit 0
fi

# Use arrays for better performance
declare -a missing_files=()
declare -a validation_errors=()

# Function to validate JSON files efficiently
validate_json() {
    local file="$1"
    if [[ -f "$file" ]] && jq empty "$file" 2>/dev/null; then
        echo "    ✅ Valid JSON: $file"
        return 0
    else
        validation_errors+=("$file: Invalid JSON format")
        echo "    ⚠️  Invalid JSON format: $file"
        return 1
    fi
}

# Function to check file patterns efficiently
check_file_pattern() {
    local file_pattern="$1"
    
    echo "  Checking: $file_pattern"
    
    # Handle glob patterns
    if [[ "$file_pattern" == *"*"* ]]; then
        # Use find for glob patterns with early exit
        if find . -name "$(basename "$file_pattern")" -type f -print -quit 2>/dev/null | grep -q .; then
            echo "    ✅ Found matches for: $file_pattern"
        else
            missing_files+=("$file_pattern")
            echo "    ❌ No files match pattern: $file_pattern"
        fi
    else
        # Direct file/directory check
        if [[ -f "$file_pattern" ]]; then
            echo "    ✅ Found: $file_pattern"
            
            # Validate specific file types
            case "$file_pattern" in
                *.json)
                    validate_json "$file_pattern"
                    ;;
                "stripes.config.js")
                    if [[ -s "$file_pattern" ]]; then
                        echo "    ✅ Valid JavaScript file"
                    else
                        validation_errors+=("$file_pattern: Empty or invalid JavaScript file")
                        echo "    ⚠️  Empty or invalid JavaScript file"
                    fi
                    ;;
            esac
        elif [[ -d "$file_pattern" ]]; then
            echo "    ✅ Found directory: $file_pattern"
        else
            missing_files+=("$file_pattern")
            echo "    ❌ Missing: $file_pattern"
        fi
    fi
}

echo "📋 Checking required files..."
# Process files more efficiently
while IFS= read -r file_pattern; do
    [[ -n "$file_pattern" ]] && check_file_pattern "$file_pattern"
done <<< "$REQUIRED_FILES"

# Report results
echo ""
echo "📊 Validation Summary"
echo "===================="

if [[ ${#missing_files[@]} -eq 0 && ${#validation_errors[@]} -eq 0 ]]; then
    echo "✅ All required files are present and valid"
    exit 0
else
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        echo "❌ Missing required files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        echo ""
    fi

    if [[ ${#validation_errors[@]} -gt 0 ]]; then
        echo "⚠️  Validation errors:"
        for error in "${validation_errors[@]}"; do
            echo "  - $error"
        done
        echo ""
    fi

    echo "::error::File validation failed. See above for details."
    exit 1
fi
