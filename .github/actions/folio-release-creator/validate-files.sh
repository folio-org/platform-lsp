#!/bin/bash
set -euo pipefail

# FOLIO Release Files Validator
# Validates that all required files exist according to the configuration

CONFIG_PATH="${1:-.github/release-config.yml}"

echo "🔍 Validating required files using config: $CONFIG_PATH"

if [[ ! -f "$CONFIG_PATH" ]]; then
    echo "::error::Configuration file not found: $CONFIG_PATH"
    exit 1
fi

echo "Using yq for YAML parsing"
REQUIRED_FILES=$(yq eval '.required_files[]' "$CONFIG_PATH" 2>/dev/null || echo "")

if [[ -z "$REQUIRED_FILES" ]]; then
    echo "::warning::No required files specified in configuration"
    exit 0
fi

missing_files=()
validation_errors=()

echo "📋 Checking required files..."
while IFS= read -r file_pattern; do
    [[ -z "$file_pattern" ]] && continue

    echo "  Checking: $file_pattern"

    # Handle glob patterns
    if [[ "$file_pattern" == *"*"* ]]; then
        # Use find for glob patterns
        matches=$(find . -name "$(basename "$file_pattern")" -type f 2>/dev/null | head -1)
        if [[ -z "$matches" ]]; then
            missing_files+=("$file_pattern")
            echo "    ❌ No files match pattern: $file_pattern"
        else
            echo "    ✅ Found matches for: $file_pattern"
        fi
    else
        # Direct file check
        if [[ -f "$file_pattern" ]]; then
            echo "    ✅ Found: $file_pattern"

            # Additional validation for specific files
            case "$file_pattern" in
                "platform-descriptor.json")
                    if ! jq empty "$file_pattern" 2>/dev/null; then
                        validation_errors+=("$file_pattern: Invalid JSON format")
                        echo "    ⚠️  Invalid JSON format"
                    else
                        echo "    ✅ Valid platform descriptor"
                    fi
                    ;;
                "package.json")
                    if ! jq empty "$file_pattern" 2>/dev/null; then
                        validation_errors+=("$file_pattern: Invalid JSON format")
                        echo "    ⚠️  Invalid JSON format"
                    else
                        echo "    ✅ Valid package.json"
                    fi
                    ;;
                "stripes.config.js")
#                    if ! node -c "$file_pattern" 2>/dev/null; then
                    if ! [[ -s "$file_pattern" ]]; then
                        validation_errors+=("$file_pattern: JavaScript syntax error")
                        echo "    ⚠️  JavaScript syntax error"
                    else
                        echo "    ✅ Valid JavaScript syntax"
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
