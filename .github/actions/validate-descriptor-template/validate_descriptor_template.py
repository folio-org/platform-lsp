#!/usr/bin/env python3
"""Validate constraint-prefixed versions in a platform descriptor template file.

Reads the template file path from the TEMPLATE_FILE environment variable.

Exit codes:
  0 - validation passed
  1 - validation failed (errors printed as GitHub Actions annotations)
"""

import json
import os
import re
import sys

# The optional suffix admits pre-release stems such as ^2.1.0-SNAPSHOT, which the
# resolvers already handle. Full semver ranges are not supported yet — see RANCHER-3069.
CONSTRAINT_RE = re.compile(r'^[\^~]?\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$')
PLAIN_VERSION_RE = re.compile(r'^(\d+\.\d+\.\d+|R\d+-\d{4})')

# 'latest' means "no window — newest in the declared preRelease channel". Kept as a
# separate alternative rather than folded into CONSTRAINT_RE, which stays semver-only.
LATEST = 'latest'

# A #<branch> pin, kept in step with update-applications.py's BRANCH_RE. Applications only:
# a pin resolves an application descriptor from that branch, and components are Docker
# images with no such artifact. Rejecting a pinned component here rather than letting the
# resolver raise puts the error where the mistake is.
BRANCH_RE = re.compile(r'^#(?!\d+\.\d+)(?!.*\.\.)[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$')

# PreReleaseFilter, as folio-application-generator defines it for application templates.
PRE_RELEASE_VALUES = ('false', 'true', 'only')


def check_entry(label: str, entry: dict, errors: list[str], allow_branch: bool = False) -> None:
    v = str(entry.get('version', ''))
    text = v.strip()
    if text.startswith('#'):
        if not allow_branch:
            errors.append(
                f"{label}.version='{v}' is a branch pin, which is only supported for applications"
            )
        elif not BRANCH_RE.match(text):
            errors.append(
                f"{label}.version='{v}' is not a valid branch pin (expected #<branch> using "
                "letters, digits, '.', '-' or '_'; no slashes, and not a bare version)"
            )
    elif text.lower() != LATEST and not CONSTRAINT_RE.match(v):
        errors.append(f"{label}.version='{v}' is invalid")

    if 'preRelease' in entry:
        pr = str(entry['preRelease']).strip().lower()
        if pr not in PRE_RELEASE_VALUES:
            errors.append(
                f"{label}.preRelease='{entry['preRelease']}' is invalid "
                f"(allowed: {', '.join(PRE_RELEASE_VALUES)})"
            )


def validate(template_file: str) -> list[str]:
    with open(template_file) as f:
        tmpl = json.load(f)

    errors = []

    if not PLAIN_VERSION_RE.match(tmpl.get('version', '')):
        errors.append("top-level 'version' must be plain X.Y.Z or Rx-YYYY")

    for comp in tmpl.get('eureka-components', []):
        check_entry(f"eureka-components[{comp['name']}]", comp, errors)

    for group, apps in tmpl.get('applications', {}).items():
        if not isinstance(apps, list):
            errors.append(f"applications.{group} must be a list")
            continue
        for app in apps:
            check_entry(f"applications.{group}[{app['name']}]", app, errors, allow_branch=True)

    return errors


def main() -> None:
    template_file = os.environ.get('TEMPLATE_FILE', '')
    if not template_file:
        print('::error::TEMPLATE_FILE environment variable is required', file=sys.stderr)
        sys.exit(1)

    errors = validate(template_file)
    if errors:
        for e in errors:
            print(f'::error::{e}')
        sys.exit(1)

    print('::notice::Template validation passed')


if __name__ == '__main__':
    main()