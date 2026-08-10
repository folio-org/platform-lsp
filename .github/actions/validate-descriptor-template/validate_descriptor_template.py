#!/usr/bin/env python3
"""Validate constraint-prefixed versions in a platform descriptor template file.

Reads the template file path from the TEMPLATE_FILE environment variable and writes
`valid` and `failure_reason` to GITHUB_OUTPUT.

Two distinct outcomes, following generate-application-descriptor in kitfox-github:

  malformed  -> exit 1. Someone wrote a constraint the resolvers cannot read.
  placeholder-> exit 0 with valid=false. release-preparation-orchestrator seeds a new
                branch with '^VERSION_<x>' for a human to replace; the branch is not ready
                yet, but it is not broken either, so the caller skips it instead of
                failing every hour until someone notices.

Exit codes:
  0 - template is usable, or is merely awaiting placeholder replacement (valid=false)
  1 - template is malformed (errors printed as GitHub Actions annotations)
"""

import json
import os
import re
import sys

# The optional suffix admits pre-release stems such as ^2.1.0-SNAPSHOT, which the
# resolvers already handle. Full semver ranges are not supported yet — see RANCHER-3069.
CONSTRAINT_RE = re.compile(r'^[\^~]?\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$')

# Anchored deliberately. release-update-flow feeds this value to calculate-version-increment,
# whose pattern requires a trailing '.<number>'; an unanchored match let a bare 'R1-2026'
# through, and the branch then reported no update and committed nothing on every run.
PLAIN_VERSION_RE = re.compile(r'^(\d+\.\d+\.\d+|R\d+-\d{4}(-[a-z0-9-]+)?(-SNAPSHOT)?(\.\d+)?)$')

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

# Seeded by release-preparation-orchestrator ('^VERSION_3.9.1') and by the Maven-substituted
# root template ('${project.version}'). Not an error — the branch simply is not ready.
PLACEHOLDER_RE = re.compile(r'^[\^~]?VERSION[_-]|\$\{')


def check_entry(label: str, entry: dict, errors: list[str], pending: list[str],
                allow_branch: bool = False) -> None:
    v = str(entry.get('version', ''))
    text = v.strip()
    if PLACEHOLDER_RE.search(text):
        pending.append(f"{label}.version='{v}'")
    elif text.startswith('#'):
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


def validate(template_file: str) -> tuple[list[str], list[str]]:
    """Return (errors, pending). Non-empty errors mean malformed; pending means not ready."""
    with open(template_file) as f:
        tmpl = json.load(f)

    errors: list[str] = []
    pending: list[str] = []

    version = str(tmpl.get('version', ''))
    if PLACEHOLDER_RE.search(version):
        pending.append(f"version='{version}'")
    elif not PLAIN_VERSION_RE.match(version):
        errors.append("top-level 'version' must be plain X.Y.Z or Rx-YYYY")

    for comp in tmpl.get('eureka-components', []):
        check_entry(f"eureka-components[{comp['name']}]", comp, errors, pending)

    for group, apps in tmpl.get('applications', {}).items():
        if not isinstance(apps, list):
            errors.append(f"applications.{group} must be a list")
            continue
        for app in apps:
            check_entry(f"applications.{group}[{app['name']}]", app, errors, pending,
                        allow_branch=True)

    return errors, pending


def emit(name: str, value: str) -> None:
    path = os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(f'{name}={value}\n')


def main() -> None:
    template_file = os.environ.get('TEMPLATE_FILE', '')
    if not template_file:
        print('::error::TEMPLATE_FILE environment variable is required', file=sys.stderr)
        sys.exit(1)

    errors, pending = validate(template_file)

    if errors:
        for e in errors:
            print(f'::error::{e}')
        emit('valid', 'false')
        emit('failure_reason', f'Invalid descriptor template: {"; ".join(errors)}')
        sys.exit(1)

    # Placeholders are a "not yet", not a "wrong". Exiting 0 lets the caller skip the branch
    # quietly instead of failing the scheduled run until someone replaces them.
    if pending:
        joined = ', '.join(pending)
        print(f'::warning::Descriptor template still holds unresolved placeholders, '
              f'skipping update: {joined}')
        emit('valid', 'false')
        emit('failure_reason', f'Template awaiting placeholder replacement: {joined}')
        return

    emit('valid', 'true')
    print('::notice::Template validation passed')


if __name__ == '__main__':
    main()