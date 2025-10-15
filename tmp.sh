#!/usr/bin/env bash
set -euo pipefail

# compare_lists "<current-json>" "<updated-json>"
compare_lists() {
  local current="$1" updated="$2"

  jq -n --argjson OLD "$current" --argjson NEW "$updated" '
    def to_map: map({key:.name, value:.version}) | from_entries;
    ($OLD|to_map) as $O | ($NEW|to_map) as $N |
    [ ($O|keys[]) as $k
      | select(($N|has($k)) and ($O[$k] != $N[$k]))
      | { name: $k, change: { old: $O[$k], new: $N[$k] } }
    ]
  '
}

UPDATED_EUREKA_COMPONENTS='[{"name":"folio-kong","version":"3.9.1"},{"name":"folio-keycloak","version":"26.1.3"},{"name":"folio-module-sidecar","version":"3.0.10"},{"name":"mgr-applications","version":"3.0.3"},{"name":"mgr-tenants","version":"3.0.3"},{"name":"mgr-tenant-entitlements","version":"3.1.7"}]'
CURRENT_EUREKA_COMPONENTS='[{"name":"folio-kong","version":"3.9.1"},{"name":"folio-keycloak","version":"26.1.3"},{"name":"folio-module-sidecar","version":"3.0.7"},{"name":"mgr-applications","version":"3.0.1"},{"name":"mgr-tenants","version":"3.0.1"},{"name":"mgr-tenant-entitlements","version":"3.1.0"}]'

UPDATED_REPORT=$(compare_lists "$CURRENT_EUREKA_COMPONENTS" "$UPDATED_EUREKA_COMPONENTS")
echo "::debug::Updated report: $UPDATED_REPORT"

