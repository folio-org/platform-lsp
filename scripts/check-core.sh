#!/usr/bin/env bash

set -e

if [ ! -f "platform-descriptor.json" ]; then
    echo "Error: platform-descriptor.json not found"
    exit 1
fi

get_latest_docker_tag() {
    local component_name="$1"
    local url="https://hub.docker.com/v2/repositories/folioci/${component_name}/tags/"
    
    echo "Checking latest tag for: $component_name" >&2
    
    local response=$(curl -s -u "$DOCKERHUB_USERNAME:$DOCKERHUB_TOKEN" "$url")
    local latest_date=$(echo "$response" | jq -r '[.results[] | select(.name == "latest") | .last_updated] | first // empty')
    local latest_day=$(echo "$latest_date" | cut -d"T" -f1)
    local matched_tag=$(echo "$response" | jq -r --arg day "$latest_day" '[.results[] | select(.name != "latest") | select(.last_updated | startswith($day)) | .name] | first // empty')
    
    if [ -z "$matched_tag" ]; then
        matched_tag=$(echo "$response" | jq -r '[.results[] | select(.name != "latest") | .name] | first // empty')
    fi

    if [ -z "$matched_tag" ]; then
        echo "No tags found for $component_name" >&2
        echo ""
    else
        echo "$matched_tag"
    fi
}

compare_versions() {
    local component_name="$1"
    local current_version="$2"
    local latest_version="$3"
    
    if [ -z "$latest_version" ]; then
        echo "[FAILED] $component_name: Unable to fetch latest version from Docker Hub (current: $current_version)"
        return 1
    fi
    
    if [ "$current_version" = "$latest_version" ]; then
        echo "[OK] $component_name: Up to date ($current_version)"
        return 0
    else
        echo "[OUTDATED] $component_name: Version mismatch"
        echo "   Current: $current_version"
        echo "   Latest:  $latest_version"
        updates_needed+=("${component_name}:${current_version}:${latest_version}")
        return 1
    fi
}

echo "=== Checking Eureka Components versions against Docker Hub ==="
echo ""

total_components=0
up_to_date=0
outdated=0
failed=0
updates_needed=()

echo "Checking Eureka Components:"
components=$(jq -c '.["eureka-components"][]' platform-descriptor.json)
while IFS= read -r component; do
    component_name=$(echo "$component" | jq -r '.name')
    current_version=$(echo "$component" | jq -r '.version')
    
    if [ -n "$component_name" ] && [ -n "$current_version" ]; then
        total_components=$((total_components + 1))
        latest_version=$(get_latest_docker_tag "$component_name")
        
        if compare_versions "$component_name" "$current_version" "$latest_version"; then
            up_to_date=$((up_to_date + 1))
        else
            if [ -z "$latest_version" ]; then
                failed=$((failed + 1))
            else
                outdated=$((outdated + 1))
            fi
        fi
        echo ""
    fi
done <<< "$components"

echo "=== Summary ==="
echo "Total components checked: $total_components"
echo "Up to date: $up_to_date"
echo "Outdated: $outdated"
echo "Failed to check: $failed"

if [ $failed -gt 0 ]; then
    echo ""
    echo "[FAILED] Some components failed to process!"
    exit 1
else
    if [ ${#updates_needed[@]} -gt 0 ]; then
        echo ""
        echo "=== Updating platform-descriptor.json ==="
        
        cp platform-descriptor.json platform-descriptor.json.backup
        echo "Created backup: platform-descriptor.json.backup"
        
        for update in "${updates_needed[@]}"; do
            IFS=':' read -r component_name current_version new_version <<< "$update"
            echo "Updating $component_name: $current_version → $new_version"
            
            jq --arg name "$component_name" --arg new_ver "$new_version" '
                (."eureka-components"[] | select(.name == $name) | .version) = $new_ver
            ' platform-descriptor.json > platform-descriptor.json.tmp && mv platform-descriptor.json.tmp platform-descriptor.json
        done
        
        echo "Updated platform-descriptor.json with ${#updates_needed[@]} version changes"
        
        if git rev-parse --git-dir > /dev/null 2>&1; then
            echo ""
            echo "=== Committing and pushing changes ==="
            
            git add platform-descriptor.json
            
            commit_message="Update Eureka component versions

Updated components:
$(printf '%s\n' "${updates_needed[@]}" | while IFS=':' read -r comp current new; do
    echo "- $comp: $current → $new"
done)"
            
            git commit -m "$commit_message"
            
            current_branch=$(git branch --show-current)
            echo "Pushing changes to $current_branch branch..."
            git push origin "$current_branch"
            
            echo "[SUCCESS] Successfully committed and pushed changes to $current_branch branch!"
        else
            echo "[WARNING] Not in a git repository - skipping commit and push"
        fi
    else
        echo ""
        echo "[INFO] No version updates needed - all components are up to date"
    fi
    
    echo ""
    if [ $outdated -gt 0 ]; then
        echo "[SUCCESS] Successfully updated $outdated component(s)!"
    else
        echo "[SUCCESS] All components are up to date!"
    fi
    exit 0
fi
