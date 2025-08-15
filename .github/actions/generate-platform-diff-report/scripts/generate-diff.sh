#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Validate input files exist
if [ ! -f "$BASE_DESCRIPTOR" ]; then
  echo "::error::Base descriptor not found: $BASE_DESCRIPTOR"
  exit 1
fi

if [ ! -f "$HEAD_DESCRIPTOR" ]; then
  echo "::error::Head descriptor not found: $HEAD_DESCRIPTOR"
  exit 1
fi

echo "::notice::Generating diff between $BASE_DESCRIPTOR and $HEAD_DESCRIPTOR"

# Function to collapse changes for a given list (base vs head)
collapse_lists() {
  local base_json="$1"
  local head_json="$2"
  local label="$3"

  jq -n \
    --argjson B "$base_json" \
    --argjson H "$head_json" \
    --arg label "$label" '
    def to_map: map({key:.name, value:.version}) | from_entries;
    ($B | to_map) as $BM |
    ($H | to_map) as $HM |
    [
      ($BM | keys[]) as $k |
      select(($HM | has($k)) and ($BM[$k] != $HM[$k])) |
      {
        name: $k,
        change: { old: $BM[$k], new: $HM[$k] },
        group: $label
      }
    ]
  '
}

# Extract components and applications from base descriptor
BASE_EC=$(jq -c '."eureka-components"' "$BASE_DESCRIPTOR")
BASE_REQ=$(jq -c '.applications.required' "$BASE_DESCRIPTOR")
BASE_OPT=$(jq -c '.applications.optional' "$BASE_DESCRIPTOR")

# Extract components and applications from head descriptor
HEAD_EC=$(jq -c '."eureka-components"' "$HEAD_DESCRIPTOR")
HEAD_REQ=$(jq -c '.applications.required' "$HEAD_DESCRIPTOR")
HEAD_OPT=$(jq -c '.applications.optional' "$HEAD_DESCRIPTOR")

# Build collapsed diffs for each section
EC_DIFF=$(collapse_lists "$BASE_EC" "$HEAD_EC" "Eureka Components")
REQ_DIFF=$(collapse_lists "$BASE_REQ" "$HEAD_REQ" "Applications (required)")
OPT_DIFF=$(collapse_lists "$BASE_OPT" "$HEAD_OPT" "Applications (optional)")

# Combine all diffs into single array
COLLAPSED_REPORT=$(jq -n \
  --argjson a "$EC_DIFF" \
  --argjson b "$REQ_DIFF" \
  --argjson c "$OPT_DIFF" \
  '$a + $b + $c')

UPDATES_CNT=$(jq 'length' <<< "$COLLAPSED_REPORT")
HAS_CHANGES="false"
[ "$UPDATES_CNT" -gt 0 ] && HAS_CHANGES="true"

echo "::notice::Found $UPDATES_CNT changes between base and head"

# Function to render markdown table
render_table() {
  local json="$1"
  if [ -z "${json:-}" ] || [ "$json" = "[]" ]; then
    echo ''
    return 0
  fi
  local count
  if ! count=$(jq 'length' <<< "$json" 2>/dev/null); then
    echo ''
    return 0
  fi
  if [ "$count" -eq 0 ]; then
    echo ''
    return 0
  fi
  echo '| Name | Old Version | New Version | Group |'
  echo '| ---- | ----------- | ----------- | ----- |'
  jq -r '.[] | "| \(.name) | \(.change.old) | \(.change.new) | \(.group) |"' <<< "$json"
}

# Generate markdown report
if [ "$HAS_CHANGES" = "false" ]; then
  MARKDOWN=$'### Application & Component Updates\n\n_No changes detected between base and head._'
else
  TABLE=$(render_table "$COLLAPSED_REPORT")
  VERSION_LINE=""
  [ -n "${PLATFORM_VERSION:-}" ] && VERSION_LINE="**Platform version:** ${PLATFORM_VERSION}"

  MARKDOWN=$(cat <<EOF
### Application & Component Updates

**Base branch:** ${RELEASE_BRANCH}
**Head branch:** ${UPDATE_BRANCH}
${VERSION_LINE}
**Changed entries:** ${UPDATES_CNT}

${TABLE}

> This table shows the collapsed diff of \`platform-descriptor.json\` between base and head branches.
EOF
  )
fi

# Output results to GITHUB_OUTPUT
{
  echo 'updates_markdown<<EOF'
  echo "$MARKDOWN"
  echo 'EOF'
} >> "$GITHUB_OUTPUT"

{
  echo 'diff_json<<EOF'
  echo "$COLLAPSED_REPORT"
  echo 'EOF'
} >> "$GITHUB_OUTPUT"

echo "updates_cnt=$UPDATES_CNT" >> "$GITHUB_OUTPUT"
echo "has_changes=$HAS_CHANGES" >> "$GITHUB_OUTPUT"

echo "::notice::Platform diff report generated successfully"

