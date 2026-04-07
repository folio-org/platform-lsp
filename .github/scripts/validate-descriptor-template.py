#!/usr/bin/env python3
"""Validate constraint-prefixed versions in a platform descriptor template file.

Usage: python3 validate-descriptor-template.py <template-file>

Exit codes:
  0 - validation passed
  1 - validation failed (errors printed as GitHub Actions annotations)
"""

import json
import re
import sys

CONSTRAINT_RE = re.compile(r'^[\^~]?\d+\.\d+\.\d+$')
PLAIN_VERSION_RE = re.compile(r'^(\d+\.\d+\.\d+|R\d+-\d{4})')


def main():
    if len(sys.argv) != 2:
        print("Usage: validate-descriptor-template.py <template-file>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        tmpl = json.load(f)

    errors = []

    if not PLAIN_VERSION_RE.match(tmpl.get('version', '')):
        errors.append("top-level 'version' must be plain X.Y.Z or Rx-YYYY")

    for comp in tmpl.get('eureka-components', []):
        v = comp.get('version', '')
        if not CONSTRAINT_RE.match(v):
            errors.append(f"eureka-components[{comp['name']}].version='{v}' is invalid")

    for group in ('required', 'optional'):
        for app in tmpl.get('applications', {}).get(group, []):
            v = app.get('version', '')
            if not CONSTRAINT_RE.match(v):
                errors.append(f"applications.{group}[{app['name']}].version='{v}' is invalid")

    if errors:
        for e in errors:
            print(f"::error::{e}")
        sys.exit(1)

    print("::notice::Template validation passed")


if __name__ == '__main__':
    main()