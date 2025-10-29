#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Generate package diff report
# Compares package.json dependencies between base and head branches and generates markdown report

echo "::group::Validating inputs"
echo "::notice::Base package: $BASE_PACKAGE"
echo "::notice::Head package: $HEAD_PACKAGE"
echo "::notice::Dependency type: $DEPENDENCY_TYPE"
echo "::endgroup::"

# Validate head package.json exists (required)
if [ ! -f "$HEAD_PACKAGE" ]; then
  echo "::error::Head package.json not found: $HEAD_PACKAGE"
  exit 1
fi

if [ ! -s "$HEAD_PACKAGE" ]; then
  echo "::error::Head package.json is empty: $HEAD_PACKAGE"
  exit 1
fi

# Validate base package.json (optional, but warn if missing)
if [ ! -f "$BASE_PACKAGE" ]; then
  echo "::warning::Base package.json not found: $BASE_PACKAGE"
  echo "::notice::No baseline available for comparison, reporting no changes"

  # Output empty results
  {
    echo 'ui_updates_markdown<<EOF'
    echo '### UI Dependency Updates'
    echo ''
    echo '_Base package.json not available for comparison._'
    echo 'EOF'
  } >> "$GITHUB_OUTPUT"

  echo 'diff_json=[]' >> "$GITHUB_OUTPUT"
  echo 'ui_updates_cnt=0' >> "$GITHUB_OUTPUT"
  echo 'has_changes=false' >> "$GITHUB_OUTPUT"

  exit 0
fi

if [ ! -s "$BASE_PACKAGE" ]; then
  echo "::warning::Base package.json is empty: $BASE_PACKAGE"
  echo "::notice::No baseline available for comparison, reporting no changes"

  # Output empty results
  {
    echo 'ui_updates_markdown<<EOF'
    echo '### UI Dependency Updates'
    echo ''
    echo '_Base package.json is empty._'
    echo 'EOF'
  } >> "$GITHUB_OUTPUT"

  echo 'diff_json=[]' >> "$GITHUB_OUTPUT"
  echo 'ui_updates_cnt=0' >> "$GITHUB_OUTPUT"
  echo 'has_changes=false' >> "$GITHUB_OUTPUT"

  exit 0
fi

echo "::group::Extracting dependencies"

# Determine jq path based on dependency type
case "$DEPENDENCY_TYPE" in
  dependencies)
    DEP_PATH='.dependencies // {}'
    DEP_LABEL='dependencies'
    ;;
  devDependencies)
    DEP_PATH='.devDependencies // {}'
    DEP_LABEL='devDependencies'
    ;;
  all)
    DEP_PATH='(.dependencies // {}) + (.devDependencies // {})'
    DEP_LABEL='all dependencies'
    ;;
  *)
    echo "::error::Invalid dependency_type: $DEPENDENCY_TYPE (must be: dependencies, devDependencies, or all)"
    exit 1
    ;;
esac

# Extract dependencies from both files
BASE_DEPS=$(jq -c "$DEP_PATH" "$BASE_PACKAGE")
HEAD_DEPS=$(jq -c "$DEP_PATH" "$HEAD_PACKAGE")

echo "::notice::Base dependencies extracted: $(jq 'length' <<< "$BASE_DEPS") items"
echo "::notice::Head dependencies extracted: $(jq 'length' <<< "$HEAD_DEPS") items"
echo "::endgroup::"

echo "::group::Building diff"

# Build collapsed diff showing only changes
DIFF_JSON=$(jq -n \
  --argjson base "$BASE_DEPS" \
  --argjson head "$HEAD_DEPS" '
  [
    ($base | keys[]) as $k |
    select(
      ($head | has($k)) and
      ($base[$k] != $head[$k])
    ) |
    {
      name: $k,
      change: {
        old: $base[$k],
        new: $head[$k]
      }
    }
  ] | sort_by(.name)
')

UPDATES_CNT=$(jq 'length' <<< "$DIFF_JSON")
HAS_CHANGES='false'
[ "$UPDATES_CNT" -gt 0 ] && HAS_CHANGES='true'

echo "::notice::Found $UPDATES_CNT dependency changes"
echo "::endgroup::"

echo "::group::Generating markdown report"

# Generate markdown report
if [ "$HAS_CHANGES" = 'false' ]; then
  MARKDOWN=$(cat <<EOF
### UI Dependency Updates

_No changes detected between base and head package.json._
EOF
  )
else
  # Build markdown table
  TABLE_HEADER=$(cat <<'EOFTABLE'
| Dependency | Old Version | New Version |
| ---------- | ----------- | ----------- |
EOFTABLE
  )

  TABLE_ROWS=$(jq -r '.[] | "| \(.name) | \(.change.old) | \(.change.new) |"' <<< "$DIFF_JSON")

  MARKDOWN=$(cat <<EOF
### UI Dependency Updates

**Base branch:** ${RELEASE_BRANCH}
**Head branch:** ${UPDATE_BRANCH}
**Updated dependencies:** ${UPDATES_CNT}

${TABLE_HEADER}
${TABLE_ROWS}

> This table shows the collapsed diff of \`package.json\` ${DEP_LABEL} between base and head branches.
EOF
  )
fi

echo "::notice::Markdown report generated (${#MARKDOWN} bytes)"
echo "::endgroup::"

# Write outputs to GITHUB_OUTPUT
{
  echo 'ui_updates_markdown<<EOF'
  echo "$MARKDOWN"
  echo 'EOF'
} >> "$GITHUB_OUTPUT"

{
  echo 'diff_json<<EOF'
  echo "$DIFF_JSON"
  echo 'EOF'
} >> "$GITHUB_OUTPUT"

echo "ui_updates_cnt=$UPDATES_CNT" >> "$GITHUB_OUTPUT"
echo "has_changes=$HAS_CHANGES" >> "$GITHUB_OUTPUT"

echo "::notice::Package diff report generation complete"

