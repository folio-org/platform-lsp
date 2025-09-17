#!/usr/bin/env python3
"""
Update Eureka components script.
"""

from typing import List, Dict
import requests

GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "folio-org"


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

        # Add your component processing logic here
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
    Get a list of releases for a repository in the folio-org organization using GitHub REST API.

    Args:
        repo_name: Name of the repository
    Returns:
        List of releases (each as dict with tag_name, name, published_at)
    Raises:
        Exception if repo not found or API error
    """
    repo_url = f"{GITHUB_API_URL}/repos/{ORG_NAME}/{repo_name}"
    releases_url = f"{repo_url}/releases"
    headers = {"Accept": "application/vnd.github+json"}

    # Check if repo exists
    repo_resp = requests.get(repo_url, headers=headers)
    if repo_resp.status_code != 200:
        raise Exception(f"Repository '{repo_name}' not found in '{ORG_NAME}' organization.")

    # Get releases
    releases_resp = requests.get(releases_url, headers=headers)
    if releases_resp.status_code != 200:
        raise Exception(f"Failed to fetch releases for '{repo_name}'.")
    releases = releases_resp.json()
    result = []
    for rel in releases:
        result.append({
            "tag_name": rel.get("tag_name"),
            "name": rel.get("name"),
            "published_at": rel.get("published_at")
        })
    return result


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
