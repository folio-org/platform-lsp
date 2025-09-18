#!/usr/bin/env python3
"""
Update application versions based on entries in the FOLIO Application Registry (FAR).
"""

from typing import List, Tuple, Optional, Sequence, Dict, Iterable
import os
import sys
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FAR_BASE_URL = os.getenv("FAR_BASE_URL", "https://far-test.ci.folio.org")
FILTER_SCOPE = os.getenv("FILTER_SCOPE", "patch").lower()  # major | minor | patch
SORT_ORDER = os.getenv("SORT_ORDER", "asc").lower()        # asc | desc
FAR_LIMIT = int(os.getenv("FAR_LIMIT", "500"))              # max records to request
FAR_LATEST = int(os.getenv("FAR_LATEST", "50"))             # FAR 'latest' param (server-side filter)
FAR_PRE_RELEASE = os.getenv("FAR_PRE_RELEASE", "false").lower() in {"1", "true", "yes"}
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10.0"))

_VALID_FILTER_SCOPES = {"major", "minor", "patch"}
_VALID_SORT_ORDERS = {"asc", "desc"}

if FILTER_SCOPE not in _VALID_FILTER_SCOPES:
    raise ValueError(f"Invalid FILTER_SCOPE='{FILTER_SCOPE}'. Allowed: {_VALID_FILTER_SCOPES}")
if SORT_ORDER not in _VALID_SORT_ORDERS:
    raise ValueError(f"Invalid SORT_ORDER='{SORT_ORDER}'. Allowed: {_VALID_SORT_ORDERS}")

# ---------------------------------------------------------------------------
# Semver helpers (numeric only). Non-numeric segments -> 0.
# ---------------------------------------------------------------------------

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


def is_newer(current: str, candidate: str) -> bool:
    return parse_semver(candidate) > parse_semver(current)

# ---------------------------------------------------------------------------
# FAR version retrieval
# ---------------------------------------------------------------------------

def fetch_app_versions(app_name: str) -> List[str]:
    """Return list of version strings for a given application name.

    FAR primary path: payload.applicationDescriptors[].version
    Fallbacks try a few common structures.
    """
    params = {
        "limit": str(FAR_LIMIT),
        "appName": app_name,
        "preRelease": str(FAR_PRE_RELEASE).lower(),
        "latest": str(FAR_LATEST),
    }
    url = f"{FAR_BASE_URL}/applications"

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:  # network-level
        print(f"fetch_app_versions: request failed for {app_name}: {exc}", file=sys.stderr)
        return []

    if resp.status_code != 200:
        print(f"fetch_app_versions: HTTP {resp.status_code} for {app_name}", file=sys.stderr)
        return []

    try:
        payload = resp.json()
    except ValueError as exc:  # JSON decode
        print(f"fetch_app_versions: invalid JSON for {app_name}: {exc}", file=sys.stderr)
        return []

    versions: List[str] = []

    # Primary extraction
    if isinstance(payload, dict):
        descriptors = payload.get("applicationDescriptors")
        if isinstance(descriptors, list):
            for item in descriptors:
                if isinstance(item, dict) and "version" in item:
                    versions.append(str(item["version"]))

    # Fallback extraction patterns
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

# ---------------------------------------------------------------------------
# Version filtering and decision logic
# ---------------------------------------------------------------------------

def filter_versions(versions: Sequence[str], base_version: str) -> List[str]:
    if not versions or not base_version:
        return []
    base = parse_semver(base_version)
    result: List[str] = []
    for v in versions:
        sem = parse_semver(v)
        if FILTER_SCOPE == "major":
            pass
        elif FILTER_SCOPE == "minor":
            if sem[0] != base[0]:
                continue
        elif FILTER_SCOPE == "patch":
            if not (sem[0] == base[0] and sem[1] == base[1]):
                continue
        result.append(v)
    result.sort(key=lambda x: parse_semver(x), reverse=(SORT_ORDER == "desc"))
    return result


def decide_update(current_version: str, candidate_versions: Sequence[str]) -> Optional[str]:
    if not candidate_versions:
        return None
    chosen = candidate_versions[0] if SORT_ORDER == "desc" else candidate_versions[-1]
    return chosen if is_newer(current_version, chosen) else None

# ---------------------------------------------------------------------------
# Update logic
# ---------------------------------------------------------------------------

def update_applications(applications: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Mutate each application record in-place if a newer version exists in scope.

    applications: list of {"name": str, "version": str}
    returns same list (for chaining)
    """
    if not applications:
        print("No applications provided")
        return applications

    print(f"Processing {len(applications)} applications (scope={FILTER_SCOPE}, order={SORT_ORDER})...")

    for app in applications:
        name = app.get("name", "<unknown>")
        current = app.get("version", "0.0.0")
        print(f"- {name}: current={current}")
        try:
            all_versions = fetch_app_versions(name)
        except Exception as exc:  # noqa: BLE001 (defensive catch, should be rare)
            print(f"  fetch error: {exc}; skipping")
            continue
        if not all_versions:
            print("  no versions found")
            continue
        filtered = filter_versions(all_versions, current)
        if not filtered:
            print("  no candidate versions in scope")
            continue
        new_version = decide_update(current, filtered)
        if not new_version:
            print("  up to date")
            continue
        app["version"] = new_version
        print(f"  updated -> {new_version}")

    return applications

# ---------------------------------------------------------------------------
# Grouped helpers (unchanged semantics)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Demo entry point
# ---------------------------------------------------------------------------
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
    update_applications(flat)

    print("\nUpdated applications:")
    print_grouped(sample_components)
