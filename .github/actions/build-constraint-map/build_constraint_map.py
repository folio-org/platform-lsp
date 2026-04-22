#!/usr/bin/env python3
"""Build per-entry constraint maps from descriptor JSON for eureka-components and applications.

Reads EUREKA_COMPONENTS and APPLICATIONS environment variables (JSON strings),
derives a constraint map (minor|patch|exact) from version prefixes (^|~|plain),
and writes component-constraint-map and app-constraint-map to GITHUB_OUTPUT.
"""

import json
import os
import sys


def extract_constraints(items: list[dict]) -> dict[str, str]:
    result = {}
    for item in items:
        v = item.get('version', '')
        if v.startswith('^'):
            result[item['name']] = 'minor'
        elif v.startswith('~'):
            result[item['name']] = 'patch'
        else:
            result[item['name']] = 'exact'
    return result


def main() -> None:
    eureka_components_json = os.environ.get('EUREKA_COMPONENTS', '')
    applications_json = os.environ.get('APPLICATIONS', '')

    if not eureka_components_json or not applications_json:
        print('::error::EUREKA_COMPONENTS and APPLICATIONS environment variables are required', file=sys.stderr)
        sys.exit(1)

    components = json.loads(eureka_components_json)
    apps_obj = json.loads(applications_json)

    component_map = extract_constraints(components)
    app_items = apps_obj.get('required', []) + apps_obj.get('optional', [])
    app_map = extract_constraints(app_items)

    gh_output = os.environ.get('GITHUB_OUTPUT', '')
    if not gh_output:
        print('::error::GITHUB_OUTPUT environment variable is not set', file=sys.stderr)
        sys.exit(1)

    with open(gh_output, 'a') as f:
        f.write(f'component-constraint-map={json.dumps(component_map)}\n')
        f.write(f'app-constraint-map={json.dumps(app_map)}\n')


if __name__ == '__main__':
    main()