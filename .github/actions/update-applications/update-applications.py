#!/usr/bin/env python3
"""Print a mock list of applications (hard-coded example) and provide helpers to
fetch available versions & update application entries based on available versions.

KISS focus. Docker image existence checks removed.
Supports grouped structure with keys 'required' and 'optional'.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import os
from typing import List, Tuple, Optional, Sequence, Dict, Iterable

# Global base address for the FOLIO Application Registry (FAR)
BASE_URL = "https://far-test.ci.folio.org"

# --- Helper functions (semver, filtering) ---

def parse_semver(version: str) -> Tuple[int, int, int]:
    parts = (version or "0").split(".")
    nums: List[int] = []
    for p in parts[:3]:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)  # type: ignore


def is_newer(a: str, b: str) -> bool:
    return parse_semver(b) > parse_semver(a)


def filter_versions(versions: Sequence[str], base_version: str, scope: str = "patch", sort_order: str = "asc") -> List[str]:
    if not versions or not base_version:
        return []
    scope = scope.lower()
    sort_order = sort_order.lower()
    base = parse_semver(base_version)
    result: List[str] = []
    for v in versions:
        sem = parse_semver(v)
        if scope == "major":
            pass
        elif scope == "minor":
            if sem[0] != base[0]:
                continue
        elif scope == "patch":
            if not (sem[0] == base[0] and sem[1] == base[1]):
                continue
        result.append(v)
    result.sort(key=lambda x: parse_semver(x), reverse=(sort_order == "desc"))
    return result


def decide_update(current_version: str, candidate_versions: Sequence[str], sort_order: str = "asc") -> Optional[str]:
    if not candidate_versions:
        return None
    newest = candidate_versions[0] if sort_order == "desc" else candidate_versions[-1]
    return newest if is_newer(current_version, newest) else None

# --- FAR version retrieval ---

def fetch_versions(app_name: str, limit: int = 500, pre_release: bool = False, latest: int = 20, timeout: float = 10.0) -> List[str]:
    """Return list of versions for app_name.

    Primary extraction path: $.applicationDescriptors.*.version
    Fallback to heuristic keys if absent.
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
                print(f"fetch_versions: HTTP {resp.status} for {app_name}", file=sys.stderr)
                return []
            try:
                payload = json.loads(resp.read().decode("utf-8"))
            except json.JSONDecodeError as e:
                print(f"fetch_versions: invalid JSON for {app_name}: {e}", file=sys.stderr)
                return []
    except urllib.error.URLError as e:
        print(f"fetch_versions: request failed for {app_name}: {e}", file=sys.stderr)
        return []

    versions: List[str] = []
    if isinstance(payload, dict):
        descriptors = payload.get("applicationDescriptors")
        if isinstance(descriptors, list):
            for item in descriptors:
                if isinstance(item, dict) and "version" in item:
                    versions.append(str(item["version"]))
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

# --- update_applications logic ---

def update_applications(applications: List[Dict[str, str]], scope: str = "patch", sort_order: str = "asc") -> List[Dict[str, str]]:
    """Update application versions in-place when a newer version is available.

    Args:
        applications: list of {"name": str, "version": str}
        scope: semver scope (major|minor|patch) controlling which newer versions are considered
        sort_order: asc or desc ordering when selecting candidate versions

    Returns:
        The same list (mutated) for convenience.
    """
    if not applications:
        print("No applications provided")
        return applications

    print(f"Processing {len(applications)} applications (scope={scope}, order={sort_order})")

    for app in applications:
        name = app.get("name", "<unknown>")
        cur = app.get("version", "0.0.0")
        print(f"- {name}: current={cur}")
        try:
            all_versions = fetch_versions(name)
        except Exception as exc:  # noqa: BLE001
            print(f"  fetch error: {exc}; skipping")
            continue
        if not all_versions:
            print("  no versions found")
            continue
        filtered = filter_versions(all_versions, cur, scope=scope, sort_order=sort_order)
        if not filtered:
            print("  no candidate versions in scope")
            continue
        new_version = decide_update(cur, filtered, sort_order=sort_order)
        if not new_version:
            print("  up to date")
            continue
        app["version"] = new_version
        print(f"  updated -> {new_version}")
    return applications

# --- helpers for grouped structure ---

def collect_grouped_apps(grouped: Dict[str, List[Dict[str, str]]], groups: Iterable[str] = ("required", "optional")) -> List[Dict[str, str]]:
    collected: List[Dict[str, str]] = []
    for g in groups:
        items = grouped.get(g, [])
        if isinstance(items, list):
            collected.extend(items)
    return collected


def print_grouped(grouped: Dict[str, List[Dict[str, str]]]) -> None:
    for g, items in grouped.items():
        print(f"{g}:")
        for app in items:
            print(f"  {app.get('name')}: {app.get('version')}")

# --- Entry point ---
if __name__ == "__main__":
    sample_components = {
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

    print("Original applications:")
    print_grouped(sample_components)

    print("\nUpdating...\n")
    flat = collect_grouped_apps(sample_components)
    update_applications(flat, scope=os.getenv("FILTER_SCOPE", "patch"), sort_order=os.getenv("SORT_ORDER", "asc"))

    print("\nUpdated applications:")
    print_grouped(sample_components)
