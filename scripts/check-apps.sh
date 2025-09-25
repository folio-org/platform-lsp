#!/usr/bin/env bash

set -e

# Check if platform-descriptor.json exists
if [ ! -f "platform-descriptor.json" ]; then
    echo "Error: platform-descriptor.json not found"
    exit 1
fi

# Function to get latest version from FAR API
get_latest_version() {
    local app_name="$1"
    local url="${FAR_URL}/applications?limit=500&appName=${app_name}&preRelease=only&latest=1"

    echo "Checking latest version for: $app_name" >&2
    
    # Fetch the response and extract both version and id fields
    local response=$(curl -s "$url")
    local latest_version=$(echo "$response" | jq -r '.applicationDescriptors[0].version // empty')
    local latest_id=$(echo "$response" | jq -r '.applicationDescriptors[0].id // empty')
    
    if [ -z "$latest_version" ] || [ -z "$latest_id" ]; then
        echo "No version found for $app_name" >&2
        echo ""
    else
        # Return both version and id separated by pipe
        echo "${latest_version}|${latest_id}"
    fi
}

# Function to compare versions
compare_versions() {
    local app_name="$1"
    local current_version="$2"
    local latest_info="$3"
    
    if [ -z "$latest_info" ]; then
        echo "❌ $app_name: Unable to fetch latest version (current: $current_version)"
        # Still add current app id to validation list even if we can't fetch latest
        app_ids+=("${app_name}-${current_version}")
        return 1
    fi
    
    # Split latest_info into version and id
    local latest_version=$(echo "$latest_info" | cut -d'|' -f1)
    local latest_id=$(echo "$latest_info" | cut -d'|' -f2)
    
    if [ "$current_version" = "$latest_version" ]; then
        echo "✅ $app_name: Up to date ($current_version)"
        # Add current app id to the list (construct from name and version)
        app_ids+=("${app_name}-${current_version}")
        return 0
    else
        echo "⚠️  $app_name: Version mismatch"
        echo "   Current: $current_version"
        echo "   Latest:  $latest_version"
        # Add newer app id to the list
        app_ids+=("$latest_id")
        # Store update information for later use
        updates_needed+=("${app_name}:${current_version}:${latest_version}")
        return 1
    fi
}

echo "=== Checking application versions against FAR registry ==="
echo "FAR Base URL: $FAR_URL"
echo ""

# Initialize counters and app IDs array
total_apps=0
up_to_date=0
outdated=0
failed=0
validation_exit_code=0
app_ids=()
updates_needed=()

# Process required applications
echo "Checking required applications:"
required_apps=$(jq -r '.applications.required[] | "\(.name)|\(.version)"' platform-descriptor.json)
while IFS='|' read -r app_name current_version; do
    if [ -n "$app_name" ]; then
        total_apps=$((total_apps + 1))
        latest_info=$(get_latest_version "$app_name")
        
        if compare_versions "$app_name" "$current_version" "$latest_info"; then
            up_to_date=$((up_to_date + 1))
        else
            if [ -z "$latest_info" ]; then
                failed=$((failed + 1))
            else
                outdated=$((outdated + 1))
            fi
        fi
        echo ""
    fi
done <<< "$required_apps"

# Process optional applications
echo "Checking optional applications:"
optional_apps=$(jq -r '.applications.optional[] | "\(.name)|\(.version)"' platform-descriptor.json)
while IFS='|' read -r app_name current_version; do
    if [ -n "$app_name" ]; then
        total_apps=$((total_apps + 1))
        latest_info=$(get_latest_version "$app_name")
        
        if compare_versions "$app_name" "$current_version" "$latest_info"; then
            up_to_date=$((up_to_date + 1))
        else
            if [ -z "$latest_info" ]; then
                failed=$((failed + 1))
            else
                outdated=$((outdated + 1))
            fi
        fi
        echo ""
    fi
done <<< "$optional_apps"

# Summary
echo "=== Summary ==="
echo "Total applications checked: $total_apps"
echo "Up to date: $up_to_date"
echo "Outdated: $outdated"
echo "Failed to check: $failed"

# Validate interfaces if we have app IDs to check
if [ ${#app_ids[@]} -gt 0 ]; then
    echo ""
    echo "=== Validating Interfaces ==="
    echo "Collected ${#app_ids[@]} application IDs for validation:"
    printf '  - %s\n' "${app_ids[@]}"
    echo ""
    
    # Construct JSON payload
    json_payload=$(printf '%s\n' "${app_ids[@]}" | jq -R . | jq -s '{applicationIds: .}')
    
    echo "Sending validation request to ${FAR_URL}/applications/validate-interfaces"
    echo "Payload:"
    echo "$json_payload" | jq .
    echo ""
    
    # Make POST request to validate interfaces
    validation_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$json_payload" \
        "${FAR_URL}/applications/validate-interfaces")
    
    echo "Validation response:"
    echo "$validation_response" | jq .
    
    # Check if validation was successful
    if echo "$validation_response" | jq -e '.errors' >/dev/null 2>&1; then
        echo ""
        echo "❌ Interface validation failed!"
        validation_exit_code=1
    else
        echo ""
        echo "✅ Interface validation successful!"
        validation_exit_code=0
        
        # Update platform-descriptor.json if there are updates and validation passed
        if [ ${#updates_needed[@]} -gt 0 ]; then
            echo ""
            echo "=== Updating platform-descriptor.json ==="
            
            # Create a backup
            cp platform-descriptor.json platform-descriptor.json.backup
            echo "Created backup: platform-descriptor.json.backup"
            
            # Apply updates
            for update in "${updates_needed[@]}"; do
                IFS=':' read -r app_name current_version new_version <<< "$update"
                echo "Updating $app_name: $current_version → $new_version"
                
                # Use jq to update the version in the JSON file
                jq --arg name "$app_name" --arg new_ver "$new_version" '
                    (.applications.required[] | select(.name == $name) | .version) = $new_ver |
                    (.applications.optional[] | select(.name == $name) | .version) = $new_ver
                ' platform-descriptor.json > platform-descriptor.json.tmp && mv platform-descriptor.json.tmp platform-descriptor.json
            done
            
            echo "Updated platform-descriptor.json with ${#updates_needed[@]} version changes"
            
            # Check if we're in a git repository
            if git rev-parse --git-dir > /dev/null 2>&1; then
                echo ""
                echo "=== Committing and pushing changes ==="
                
                # Add the updated file
                git add platform-descriptor.json
                
                # Create commit message
                commit_message="Update application versions

Updated applications:
$(printf '%s\n' "${updates_needed[@]}" | while IFS=':' read -r app current new; do
    echo "- $app: $current → $new"
done)

Interface validation: PASSED"
                
                # Commit the changes
                git commit -m "$commit_message"
                
                # Push to current branch
                current_branch=$(git branch --show-current)
                echo "Pushing changes to $current_branch branch..."
                git push origin "$current_branch"
                
                echo "✅ Successfully committed and pushed changes to $current_branch branch!"
            else
                echo "⚠️  Not in a git repository - skipping commit and push"
            fi
        else
            echo ""
            echo "ℹ️  No version updates needed - all applications are up to date"
        fi
    fi
else
    echo ""
    echo "⚠️  No application IDs collected for validation"
    validation_exit_code=0
fi

# Exit with appropriate code
# Only exit with failure if there were actual failures (not just updates needed)
if [ $failed -gt 0 ] || [ $validation_exit_code -ne 0 ]; then
    echo ""
    echo "❌ Some applications failed to process!"
    exit 1
else
    echo ""
    if [ $outdated -gt 0 ]; then
        echo "✅ Successfully updated $outdated applications and validated interfaces!"
    else
        echo "✅ All applications are up to date and interfaces are valid!"
    fi
    exit 0
fi