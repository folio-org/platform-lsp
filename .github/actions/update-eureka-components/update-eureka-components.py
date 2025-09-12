#!/usr/bin/env python3
"""
Update Eureka components script.

Resolves newer component versions from GitHub releases when Docker images exist.
Honors semantic versioning scope (major/minor/patch) and sort order preferences.
"""

from typing import List, Dict, Sequence, Tuple, Optional, Any
import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("eureka-updater")

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "folio-org"
DOCKER_HUB_ORG = "folioorg"

# Load environment variables from .env file (optional local usage)
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DOCKER_USERNAME = os.getenv("DOCKER_USERNAME")
DOCKER_PASSWORD = os.getenv("DOCKER_PASSWORD")

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2
RETRY_INITIAL_WAIT = 1  # seconds

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_configuration(filter_scope: str, sort_order: str) -> None:
    """Validate environment configuration before proceeding."""
    _VALID_FILTER_SCOPES = {"major", "minor", "patch"}
    _VALID_SORT_ORDERS = {"asc", "desc"}

    if filter_scope not in _VALID_FILTER_SCOPES:
        raise ValueError(f"Invalid filter_scope='{filter_scope}'. Allowed: {_VALID_FILTER_SCOPES}")

    if sort_order not in _VALID_SORT_ORDERS:
        raise ValueError(f"Invalid sort_order='{sort_order}'. Allowed: {_VALID_SORT_ORDERS}")

    # No validation for tokens - they're optional

# ---------------------------------------------------------------------------
# Semver helpers (minimal – numeric only, non-numeric parts treated as 0)
# ---------------------------------------------------------------------------
def parse_semver(version: str) -> Tuple[int, int, int]:
    """
    Parse semantic version strings into (major, minor, patch) tuples.
    Non-numeric parts treated as 0.
    """
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
    """Return True if version b is newer (greater) than version a."""
    return parse_semver(b) > parse_semver(a)

# ---------------------------------------------------------------------------
# External service interactions
# ---------------------------------------------------------------------------
def build_github_headers() -> Dict[str, str]:
    """Build headers for GitHub API requests, including auth if available."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def with_retries(func):
    """Decorator for retrying API calls with exponential backoff."""
    def wrapper(*args, **kwargs):
        retries = 0
        last_error = None

        while retries <= MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except requests.RequestException as exc:
                last_error = exc
                if hasattr(exc.response, 'status_code') and exc.response.status_code == 429:
                    # Rate limited - get retry-after if available
                    retry_after = int(exc.response.headers.get('Retry-After', RETRY_INITIAL_WAIT))
                    logger.warning(f"Rate limited. Waiting {retry_after}s before retry.")
                    time.sleep(retry_after)
                else:
                    # Exponential backoff with small random jitter
                    wait_time = RETRY_INITIAL_WAIT * (RETRY_BACKOFF_BASE ** retries) + (time.time() % 1)
                    if retries < MAX_RETRIES:
                        logger.warning(f"Request failed: {exc}. Retrying in {wait_time:.1f}s ({retries+1}/{MAX_RETRIES})")
                        time.sleep(wait_time)

            retries += 1

        # If we get here, we've exhausted retries
        logger.error(f"Failed after {MAX_RETRIES} retries: {last_error}")
        raise last_error

    return wrapper


@with_retries
def fetch_repo_release_tags(repo: str, session: Optional[requests.Session] = None) -> List[str]:
    """Return plain (no leading 'v') tag names for releases in org repository."""
    sess = session or requests.Session()
    repo_url = f"{GITHUB_API_URL}/repos/{ORG_NAME}/{repo}"
    releases_url = f"{repo_url}/releases"
    headers = build_github_headers()

    # First verify repo exists
    repo_resp = sess.get(repo_url, headers=headers)
    if repo_resp.status_code != 200:
        raise RuntimeError(f"Repository '{repo}' not found in '{ORG_NAME}'.")

    # Then get releases
    rel_resp = sess.get(releases_url, headers=headers)
    if rel_resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch releases for '{repo}' (status {rel_resp.status_code}).")

    releases = rel_resp.json() or []
    tags = [r.get("tag_name") for r in releases if r.get("tag_name")]

    # Strip leading v/V
    cleaned = [t[1:] if t and t[0] in ("v", "V") and len(t) > 1 else t for t in tags]
    return cleaned


def docker_hub_auth_token(session: requests.Session) -> Optional[str]:
    """Get Docker Hub authentication token if credentials are provided."""
    if not (DOCKER_USERNAME and DOCKER_PASSWORD):
        return None
    try:
        resp = session.post("https://hub.docker.com/v2/users/login/", json={
            "username": DOCKER_USERNAME,
            "password": DOCKER_PASSWORD
        })
        if resp.status_code == 200:
            return resp.json().get("token")
    except Exception as exc:
        logger.warning(f"Docker Hub auth failed: {exc}")
    return None


@with_retries
def docker_image_exists(image: str, version: str, session: Optional[requests.Session] = None) -> bool:
    """Check if a Docker image with specific tag exists on Docker Hub."""
    sess = session or requests.Session()
    headers: Dict[str, str] = {}
    token = docker_hub_auth_token(sess)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://hub.docker.com/v2/repositories/{DOCKER_HUB_ORG}/{image}/tags/{version}"
    try:
        resp = sess.get(url, headers=headers)
        return resp.status_code == 200
    except Exception as exc:
        logger.warning(f"Docker Hub request failed: {exc}")
        return False

# ---------------------------------------------------------------------------
# Version filtering logic
# ---------------------------------------------------------------------------
def filter_versions(versions: Sequence[str], base_version: str, filter_scope: str) -> List[str]:
    """Filter versions by configured filter_scope relative to base_version."""
    if not versions or not base_version:
        return []

    base = parse_semver(base_version)
    result: List[str] = []

    for v in versions:
        sem = parse_semver(v)
        if filter_scope == "major":
            pass  # all included
        elif filter_scope == "minor":
            if sem[0] != base[0]:
                continue
        elif filter_scope == "patch":
            if not (sem[0] == base[0] and sem[1] == base[1]):
                continue
        result.append(v)

    return result

# ---------------------------------------------------------------------------
# Core update logic
# ---------------------------------------------------------------------------
def decide_update(current_version: str, candidate_versions: Sequence[str], sort_order: str) -> Optional[str]:
    """Return the best newer version (according to sort order) or None if no update."""
    if not candidate_versions:
        return None

    # Sort versions according to sort_order
    sorted_versions = sorted(candidate_versions, key=lambda x: parse_semver(x), reverse=(sort_order == "desc"))
    newest = sorted_versions[0] if sort_order == "desc" else sorted_versions[-1]
    return newest if is_newer(current_version, newest) else None


def update_components(components: List[Dict[str, str]], filter_scope: str, sort_order: str) -> List[Dict[str, str]]:
    """
    Update component versions in-place when a newer release (with existing Docker image) is found.
    Returns the same list (mutated) for convenience.
    """
    if not components:
        logger.info("No components to process")
        return components

    logger.info(f"Processing {len(components)} components (scope={filter_scope}, order={sort_order})...")
    start_time = datetime.now()
    session = requests.Session()
    updated_count = 0

    for comp in components:
        name = comp.get("name", "unknown")
        current_version = comp.get("version", "0.0.0")
        logger.info(f"Processing: {name} (current: {current_version})")

        try:
            all_tags = fetch_repo_release_tags(name, session=session)
            filtered = filter_versions(all_tags, current_version, filter_scope)
            logger.info(f"  Filtered versions: {filtered}")

            new_version = decide_update(current_version, filtered, sort_order)
            if not new_version:
                logger.info("  - Up to date")
                continue

            if not docker_image_exists(name, new_version, session=session):
                logger.info(f"  - Docker image missing for {name}:{new_version}; skipping.")
                continue

            # Apply the update
            logger.info(f"  - Applying update {name}: {current_version} -> {new_version}")
            comp["version"] = new_version
            updated_count += 1

        except Exception as exc:
            logger.error(f"  Error processing {name}: {exc}")
            logger.info(f"  Skipping update logic for {name} (keeping version {current_version})")
            continue

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"Completed processing in {elapsed:.2f}s. Updated {updated_count}/{len(components)} components.")
    return components

# ---------------------------------------------------------------------------
# Command line argument parsing
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Update Eureka components')
    parser.add_argument('--filter-scope', choices=['major', 'minor', 'patch'], default='patch',
                        help='Scope of update consideration: major/minor/patch (default: patch)')
    parser.add_argument('--sort-order', choices=['asc', 'desc'], default='asc',
                        help='Sort order when evaluating versions (default: asc)')
    parser.add_argument('--data', type=str, help='JSON string containing component data')
    return parser.parse_args()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    """Main entry point with proper error handling and return code."""
    try:
        # Parse command line arguments
        args = parse_args()
        filter_scope = args.filter_scope.lower()
        sort_order = args.sort_order.lower()

        validate_configuration(filter_scope, sort_order)

        # Check for command line data
        components_data = None
        if args.data:
            try:
                components_data = json.loads(args.data)
            except json.JSONDecodeError as exc:
                logger.error(f"Invalid JSON data provided via --data: {exc}")
                return 1

        # If no data provided, exit with error
        if components_data is None:
            logger.error("No component data provided. Use --data argument to provide components.")
            return 1

        # Validate input data structure
        if not isinstance(components_data, list):
            raise ValueError("Component data must be a JSON array of objects with name/version")
        for idx, item in enumerate(components_data):
            if not isinstance(item, dict) or "name" not in item or "version" not in item:
                raise ValueError(f"Item at index {idx} must be an object with 'name' and 'version'")

        # Log original components
        logger.info("Original components:")
        for c in components_data:
            logger.info(f" - {c['name']}: {c['version']}")

        logger.info("=" * 40)
        # Process the components
        updated = update_components(components_data, filter_scope, sort_order)
        logger.info("=" * 40)

        # Log updated components
        logger.info("Updated components:")
        for c in updated:
            logger.info(f" - {c['name']}: {c['version']}")

        # Serialize the updated components
        serialized = json.dumps(updated, separators=(",", ":"), sort_keys=True)

        # Write to GitHub outputs if running in GitHub Actions
        gh_output = os.getenv("GITHUB_OUTPUT")
        if gh_output:
            try:
                with open(gh_output, "a", encoding="utf-8") as fh:
                    fh.write(f"updated-components={serialized}\n")
                logger.info(f"GitHub output written to {gh_output}")
            except Exception as exc:
                logger.error(f"Failed writing GITHUB_OUTPUT: {exc}")
                return 1

        # Also print to stdout for logging / capture
        print(serialized)
        return 0

    except Exception as exc:
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
