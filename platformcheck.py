#!/usr/bin/env python3
"""
Release flow utilities for FOLIO LSP platform.
"""

import json
import logging
import os
import requests
from dotenv import load_dotenv

# Constants
GITHUB_API_BASE = "https://api.github.com"
DOCKERHUB_API_BASE = "https://hub.docker.com/v2"
FAR_API_BASE = "https://far.ci.folio.org"
DEFAULT_PER_PAGE = 50
DEFAULT_FAR_LIMIT = 500

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()


def read_platform_descriptor(file_path="platform-descriptor.json"):
    """Read and parse platform-descriptor.json file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Platform descriptor file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in platform descriptor: {e}")


def get_github_headers():
    """Get GitHub API headers with token validation."""
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token or github_token == 'your_github_token_here':
        raise ValueError("GitHub token not found in .env file. Please set GITHUB_TOKEN.")

    return {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'FOLIO-Release-Flow-Script'
    }


def fetch_github_versions(repo_name):
    """Fetch versions from GitHub repository tags."""
    try:
        headers = get_github_headers()
        url = f"{GITHUB_API_BASE}/repos/folio-org/{repo_name}/tags"
        response = requests.get(url, headers=headers, params={'per_page': DEFAULT_PER_PAGE})
        response.raise_for_status()

        versions = []
        for tag in response.json():
            if tag_name := tag.get("name"):
                clean_version = tag_name.lstrip('v')
                if clean_version not in versions:  # Simple deduplication
                    versions.append(clean_version)
        return versions
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch GitHub versions for {repo_name}: {e}")
        return []


def fetch_far_versions(app_name):
    """Fetch versions from FAR endpoint."""
    try:
        url = f"{FAR_API_BASE}/applications"
        response = requests.get(url, params={'limit': DEFAULT_FAR_LIMIT, 'query': f'name={app_name}'})
        response.raise_for_status()

        data = response.json()
        versions = []
        for app in data.get('applicationDescriptors', []):
            if version := app.get('version'):
                if version not in versions:  # Simple deduplication
                    versions.append(version)
        return versions
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch FAR versions for {app_name}: {e}")
        return []


def check_docker_image_exists(name, version):
    """Check if Docker image exists in DockerHub."""
    try:
        url = f"{DOCKERHUB_API_BASE}/repositories/folioorg/{name}/tags/{version}/"
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False


def parse_version(version):
    """Parse version string into comparable parts."""
    parts = version.replace('-', '.').split('.')
    parsed = []
    for part in parts:
        if part.isdigit():
            parsed.append(int(part))
        else:
            parsed.append(part.lower())
    return parsed


def sort_versions(versions):
    """Sort versions in descending order."""
    if not versions:
        return []
    try:
        return sorted(versions, key=parse_version, reverse=True)
    except (ValueError, TypeError):
        return sorted(versions, reverse=True)


def get_patch_versions(versions, base_version):
    """Get patch versions for a given base version."""
    if not versions or not base_version:
        return []

    try:
        base_parts = base_version.split('.')
        if len(base_parts) < 2:
            return []

        base_major = int(base_parts[0]) if base_parts[0].isdigit() else 0
        base_minor = int(base_parts[1]) if base_parts[1].isdigit() else 0

        patch_versions = []
        for version in versions:
            parts = version.split('.')
            if len(parts) >= 2:
                major = int(parts[0]) if parts[0].isdigit() else 0
                minor = int(parts[1]) if parts[1].isdigit() else 0
                if major == base_major and minor == base_minor:
                    patch_versions.append(version)

        return patch_versions
    except (ValueError, IndexError):
        return []


def get_latest_version(current_version, available_versions):
    """Get the latest available version, or current if no updates."""
    if not available_versions:
        return current_version, False

    patch_versions = get_patch_versions(available_versions, current_version)
    if not patch_versions:
        return current_version, False

    sorted_patches = sort_versions(patch_versions)
    latest = sorted_patches[0]

    # Simple version comparison
    if latest != current_version:
        try:
            latest_parsed = parse_version(latest)
            current_parsed = parse_version(current_version)
            if latest_parsed > current_parsed:
                return latest, True
        except (ValueError, TypeError):
            pass

    return current_version, False


class ComponentChecker:
    """Unified component checker for both eureka components and applications."""

    def __init__(self, check_docker=True):
        self.check_docker = check_docker
        self.updates_made = False

    def check_component(self, component, version_fetcher):
        """Check a single component for updates."""
        name = component.get('name')
        current_version = component.get('version')

        if not name or not current_version:
            logger.warning(f"Skipping component with missing name or version: {component}")
            return False

        logger.info(f"Checking {name} (current: {current_version})")

        # Fetch available versions
        versions = version_fetcher(name)
        if not versions:
            logger.warning(f"No versions found for {name}")
            return False

        sorted_versions = sort_versions(versions)
        logger.info(f"Found {len(sorted_versions)} versions for {name}")

        # Check for updates
        latest_version, has_update = get_latest_version(current_version, sorted_versions)

        if has_update:
            logger.info(f"Update available for {name}: {current_version} → {latest_version}")

            # Check Docker availability if required
            if self.check_docker:
                if check_docker_image_exists(name, latest_version):
                    logger.info(f"Docker image available for {name}:{latest_version}")
                    component['version'] = latest_version
                    logger.info(f"Updated {name}: {current_version} → {latest_version}")
                    return True
                else:
                    logger.warning(f"Docker image not available for {name}:{latest_version}")
                    return False
            else:
                # No Docker check needed (for applications)
                component['version'] = latest_version
                logger.info(f"Updated {name}: {current_version} → {latest_version}")
                return True
        else:
            logger.info(f"{name} is up to date ({current_version})")
            return False

    def check_components(self, components, version_fetcher, component_type):
        """Check a list of components."""
        logger.info(f"=" * 60)
        logger.info(f"CHECKING {component_type.upper()}")
        logger.info(f"=" * 60)

        updates_made = False
        for component in components:
            if self.check_component(component, version_fetcher):
                updates_made = True

        return updates_made


def check_eureka_components(descriptor):
    """Check eureka-components for updates."""
    checker = ComponentChecker(check_docker=True)
    components = descriptor.get('eureka-components', [])
    return checker.check_components(components, fetch_github_versions, "eureka components")


def check_applications(descriptor):
    """Check applications for updates."""
    checker = ComponentChecker(check_docker=False)
    updates_made = False

    applications = descriptor.get('applications', {})

    # Check required applications
    required_apps = applications.get('required', [])
    if required_apps:
        updates_made |= checker.check_components(required_apps, fetch_far_versions, "required applications")

    # Check optional applications
    optional_apps = applications.get('optional', [])
    if optional_apps:
        updates_made |= checker.check_components(optional_apps, fetch_far_versions, "optional applications")

    return updates_made


def save_platform_descriptor(descriptor, file_path="platform-descriptor.json"):
    """Save updated platform descriptor to file."""
    try:
        with open(file_path, 'w') as file:
            json.dump(descriptor, file, indent=2)
        logger.info(f"Platform descriptor saved to {file_path}")
    except IOError as e:
        raise IOError(f"Failed to save platform descriptor: {e}")


def main():
    """Main execution function."""
    try:
        descriptor = read_platform_descriptor()

        logger.info("FOLIO LSP Platform Descriptor")
        logger.info("=" * 40)
        logger.info(f"Name: {descriptor['name']}")
        logger.info(f"Version: {descriptor['version']}")

        # Check components and applications
        updates_made = check_eureka_components(descriptor)
        updates_made |= check_applications(descriptor)

        # Save if updates were made
        if updates_made:
            save_platform_descriptor(descriptor)
            logger.info("Platform descriptor updated and saved")
        else:
            logger.info("No updates needed - all components are up to date")

        total_components = len(descriptor.get('eureka-components', []))
        total_apps = len(descriptor.get('applications', {}).get('required', [])) + \
                    len(descriptor.get('applications', {}).get('optional', []))
        logger.info(f"Finished checking {total_components} components and {total_apps} applications")

    except Exception as e:
        logger.error(f"Script failed: {e}")
        raise


if __name__ == "__main__":
    main()
