#!/usr/bin/env python3
"""Print a mock list of applications (hard-coded example) and provide a helper to
fetch available versions for a given application name from the FOLIO Application Registry.

KISS: Existing behavior (printing mock data) unchanged. Added function `fetch_versions`.
Output format for printing: <group> <name> <version> (tab separated)
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import List

# Global base address for the FOLIO Application Registry (FAR)
BASE_URL = "https://far-test.ci.folio.org"

DATA = {
    "required": [
        {"name": "app-platform-minimal", "version": "2.0.19"},
        {"name": "app-platform-complete", "version": "2.1.40"},
    ],
    "optional": [
        {"name": "app-acquisitions", "version": "1.0.17"},
        {"name": "app-bulk-edit", "version": "1.0.7"},
        {"name": "app-consortia", "version": "1.2.1"},
        {"name": "app-dcb", "version": "1.1.4"},
        {"name": "app-edge-complete", "version": "2.0.9"},
        {"name": "app-erm-usage", "version": "2.0.3"},
        {"name": "app-fqm", "version": "1.0.11"},
        {"name": "app-marc-migrations", "version": "2.0.1"},
        {"name": "app-oai-pmh", "version": "1.0.2"},
        {"name": "app-inn-reach", "version": "1.0.0"},
        {"name": "app-linked-data", "version": "1.1.6"},
        {"name": "app-reading-room", "version": "2.0.2"},
        {"name": "app-consortia-manager", "version": "1.1.1"},
    ],
}


def fetch_versions(app_name: str, limit: int = 500, pre_release: bool = False, latest: int = 20, timeout: float = 10.0) -> List[str]:
    """Return a list of available version strings for the given application name.

    Extraction logic now explicitly targets JSON path: $.applicationDescriptors.*.version
    (i.e. look for top-level key 'applicationDescriptors' containing a list of objects that
    each have a 'version' field). Falls back to previous heuristics if absent.
    """
    params = {
        "limit": str(limit),
        "appName": app_name,
        "preRelease": str(pre_release).lower(),
        "latest": str(latest),
    }
    url = f"{BASE_URL}/applications?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                print(f"fetch_versions: HTTP {resp.status} for {url}", file=sys.stderr)
                return []
            try:
                payload = json.loads(resp.read().decode("utf-8"))
            except json.JSONDecodeError as e:
                print(f"fetch_versions: invalid JSON: {e}", file=sys.stderr)
                return []
    except urllib.error.URLError as e:
        print(f"fetch_versions: request failed: {e}", file=sys.stderr)
        return []

    versions: List[str] = []

    # Primary: $.applicationDescriptors.*.version
    if isinstance(payload, dict):
        descriptors = payload.get("applicationDescriptors")
        if isinstance(descriptors, list):
            for item in descriptors:
                if isinstance(item, dict) and "version" in item:
                    versions.append(str(item["version"]))

    # Fallbacks (retain prior heuristic behavior if primary produced nothing)
    if not versions:
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and "version" in item:
                    versions.append(str(item["version"]))
        elif isinstance(payload, dict):
            apps = payload.get("applications")
            if isinstance(apps, list):
                for item in apps:
                    if isinstance(item, dict) and "version" in item:
                        versions.append(str(item["version"]))
            elif "version" in payload:
                versions.append(str(payload["version"]))

    return versions


def main() -> None:
    for group, items in DATA.items():
        for app in items:
            print(f"{group}\t{app.get('name')}\t{app.get('version')}")
            versions = fetch_versions(app.get('name'))
            print(f"available\t{app.get('name')}\t{','.join(versions) if versions else '<none>'}")

if __name__ == "__main__":
    main()
