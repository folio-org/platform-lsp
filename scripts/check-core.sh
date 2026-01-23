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
    local latest_tag=$(echo "$response" | jq -r '.results[0].name // empty')
    
    if [ -z "$latest_tag" ]; then
        echo "No tags found for $component_name" >&2
        echo ""
    else
        echo "$latest_tag"
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
echo "$components" | while IFS= read -r component; do
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
done

echo "=== Summary ==="
echo "Total components checked: $total_components"
echo "Up to date: $up_to_date"
echo "Outdated: $outdated"
echo "Failed to check: $failed"
echo ""

if [ $failed -gt 0 ]; then
    echo "[FAILED] Some components failed to process!"
    exit 1
else
    if [ $outdated -gt 0 ]; then
        echo "[SUCCESS] All components checked! $outdated component(s) have updates available."
    else
        echo "[SUCCESS] All components are up to date!"
    fi
    exit 0
fi
