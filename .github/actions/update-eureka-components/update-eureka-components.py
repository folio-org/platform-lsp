#!/usr/bin/env python3
"""
Update Eureka components script.
"""

from typing import List, Dict
import requests
import os
from dotenv import load_dotenv

GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "folio-org"

FILTER_BY = "patch"  # must be one of ["major", "minor", "patch"]
SORT_BY = "asc"     # must be one of ["asc", "desc"]

# Load environment variables from .env file
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def process_components(components: List[Dict[str, str]]) -> None:
    """
    Process a list of components with name and version.

    Args:
        components: List of dictionaries containing 'name' and 'version' keys

    Example:
        components = [
            {"name": "folio-kong", "version": "3.9.1"},
            {"name": "folio-keycloak", "version": "26.1.3"}
        ]
        process_components(components)
    """
    if not components:
        print("No components to process")
        return

    print(f"Processing {len(components)} components...")

    for component in components:
        name = component.get("name", "unknown")
        version = component.get("version", "unknown")

        print(f"Processing component: {name} (version: {version})")

        try:
            releases = get_repo_releases(name)
            filtered_releases = filter_and_sort_versions(releases, version)
            print(f"  Filtered/sorted release tags for {name}: {filtered_releases}")
            if filtered_releases:
                latest_version = filtered_releases[-1] if SORT_BY == "asc" else filtered_releases[0]
                update_needed = is_update_needed(version, latest_version)
                print(f"  Latest version: {latest_version}. Update needed: {update_needed}")
                if update_needed:
                    _update_component(name, latest_version)
                else:
                    print(f"  - {name} is up to date.")
            else:
                print(f"  No filtered releases found for {name}.")
        except Exception as e:
            print(f"  Could not fetch releases: {e}")
            _update_component(name, version)


def _update_component(name: str, version: str) -> None:
    """
    Update a single component.

    Args:
        name: Component name
        version: Component version
    """
    # Placeholder for actual update logic
    # This is where you would add the specific logic for updating each component
    print(f"  - Updating {name} to version {version}")


def get_repo_releases(repo_name: str) -> list:
    """
    Get a plain list of release tag names (semver only, no 'v' prefix) for a repository in the folio-org organization using GitHub REST API.

    Args:
        repo_name: Name of the repository
    Returns:
        List of release tag names (e.g. ["3.0.1", "3.0.2"])
    Raises:
        Exception if repo not found or API error
    """
    repo_url = f"{GITHUB_API_URL}/repos/{ORG_NAME}/{repo_name}"
    releases_url = f"{repo_url}/releases"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}" if GITHUB_TOKEN else None
    }
    # Remove None values from headers
    headers = {k: v for k, v in headers.items() if v is not None}

    # Check if repo exists
    repo_resp = requests.get(repo_url, headers=headers)
    if repo_resp.status_code != 200:
        raise Exception(f"Repository '{repo_name}' not found in '{ORG_NAME}' organization.")

    # Get releases
    releases_resp = requests.get(releases_url, headers=headers)
    if releases_resp.status_code != 200:
        raise Exception(f"Failed to fetch releases for '{repo_name}'.")
    releases = releases_resp.json()
    tags = [rel.get("tag_name") for rel in releases if rel.get("tag_name")]
    # Remove leading 'v' or 'V' from tag names if present
    plain_tags = [tag[1:] if tag and (tag.startswith("v") or tag.startswith("V")) and len(tag) > 1 else tag for tag in tags]
    return plain_tags


def filter_and_sort_versions(versions: list, base_version: str) -> list:
    """
    Filter and sort a list of semver version strings by FILTER_BY and SORT_BY globals,
    keeping only those matching the relevant part of base_version.

    FILTER_BY logic:
    - "major": all tags (no filtering)
    - "minor": all tags with the same major (e.g. 3.x.y)
    - "patch": all tags with the same major and minor (e.g. 3.1.x)

    Args:
        versions: List of semver strings (e.g. ["3.0.1", "3.1.0", ...])
        base_version: The version string to filter by (e.g. "3.1.0")
    Returns:
        Filtered and sorted list of versions.
    """
    if not versions or not base_version:
        return []

    def parse_semver(ver):
        parts = ver.split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])

    base_semver = parse_semver(base_version)
    filtered = []
    for v in versions:
        semver = parse_semver(v)
        if FILTER_BY == "major":
            filtered.append(v)
        elif FILTER_BY == "minor":
            if semver[0] == base_semver[0]:
                filtered.append(v)
        elif FILTER_BY == "patch":
            if semver[0] == base_semver[0] and semver[1] == base_semver[1]:
                filtered.append(v)
    filtered.sort(key=parse_semver, reverse=(SORT_BY == "desc"))
    return filtered


def is_update_needed(current_version: str, latest_version: str) -> bool:
    """
    Compare current_version and latest_version (semver strings).
    Returns True if latest_version is greater than current_version, else False.
    """
    def parse_semver(ver):
        parts = ver.split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])
    return parse_semver(latest_version) > parse_semver(current_version)


if __name__ == "__main__":
    # Example usage
    sample_components = [
        {"name": "folio-kong", "version": "3.9.1"},
        {"name": "folio-keycloak", "version": "26.1.3"},
        {"name": "folio-module-sidecar", "version": "3.0.7"},
        {"name": "mgr-applications", "version": "3.0.1"},
        {"name": "mgr-tenants", "version": "3.0.1"},
        {"name": "mgr-tenant-entitlements", "version": "3.1.0"}
    ]

    process_components(sample_components)
