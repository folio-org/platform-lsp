#!/usr/bin/env python3
"""
Update application versions based on entries in the FOLIO Application Registry (FAR).

Resolves newer application versions by consulting the FOLIO Application Registry.
Honors semantic versioning scope (major/minor/patch) and sort order preferences.
"""

from typing import List, Tuple, Optional, Sequence, Dict, Iterable, Any, Union, cast
import os
import sys
import time
import requests
import json
import logging
import argparse
from datetime import datetime
from functools import lru_cache

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("app-updater")

FAR_BASE_URL = os.getenv("FAR_BASE_URL", "https://far.ci.folio.org")
FILTER_SCOPE = os.getenv("FILTER_SCOPE", "patch").lower()  # major | minor | patch
SORT_ORDER = os.getenv("SORT_ORDER", "asc").lower()        # asc | desc
FAR_LIMIT = int(os.getenv("FAR_LIMIT", "500"))              # max records to request
FAR_LATEST = int(os.getenv("FAR_LATEST", "50"))             # FAR 'latest' param (server-side filter)
FAR_PRE_RELEASE = os.getenv("FAR_PRE_RELEASE", "false").lower() in {"1", "true", "yes"}
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))            # HTTP request retries
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "1.0"))    # Base backoff time in seconds

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

# ---------------------------------------------------------------------------
# Semver helpers (numeric only). Non-numeric segments -> 0.
# ---------------------------------------------------------------------------
def parse_semver(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string into a tuple of (major, minor, patch) integers.

    Non-numeric segments are treated as 0.
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


def is_newer(current: str, candidate: str) -> bool:
    """Compare two version strings and return True if candidate is newer than current."""
    return parse_semver(candidate) > parse_semver(current)

# ---------------------------------------------------------------------------
# HTTP Request with retries
# ---------------------------------------------------------------------------
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
                    retry_after = int(exc.response.headers.get('Retry-After', RETRY_BACKOFF))
                    logger.warning(f"Rate limited. Waiting {retry_after}s before retry.")
                    time.sleep(retry_after)
                else:
                    # Exponential backoff with small random jitter
                    wait_time = RETRY_BACKOFF * (2 ** retries) + (time.time() % 1)
                    if retries < MAX_RETRIES:
                        logger.warning(f"Request failed: {exc}. Retrying in {wait_time:.1f}s ({retries+1}/{MAX_RETRIES})")
                        time.sleep(wait_time)

            retries += 1

        # If we get here, we've exhausted retries
        logger.error(f"Failed after {MAX_RETRIES} retries: {last_error}")
        raise last_error

    return wrapper

# ---------------------------------------------------------------------------
# FAR version retrieval
# ---------------------------------------------------------------------------
@with_retries
@lru_cache(maxsize=128)
def fetch_app_versions(app_name: str) -> List[str]:
    """Return list of version strings for a given application name.

    FAR primary path: payload.applicationDescriptors[].version
    Fallbacks try a few common structures.

    Results are cached to reduce redundant API calls.
    """
    params = {
        "limit": str(FAR_LIMIT),
        "appName": app_name,
        "preRelease": str(FAR_PRE_RELEASE).lower(),
        "latest": str(FAR_LATEST),
    }
    url = f"{FAR_BASE_URL}/applications"

    logger.debug(f"Fetching versions for {app_name} from {url}")
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()

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

    logger.debug(f"Found {len(versions)} versions for {app_name}")
    return versions

# ---------------------------------------------------------------------------
# Version filtering and decision logic
# ---------------------------------------------------------------------------
def filter_versions(versions: Sequence[str], base_version: str, filter_scope: str) -> List[str]:
    """Filter versions based on the configured scope (major, minor, patch).

    Returns a sorted list of versions that match the scope constraints.
    """
    if not versions or not base_version:
        return []
    base = parse_semver(base_version)
    result: List[str] = []
    for v in versions:
        sem = parse_semver(v)
        if filter_scope == "major":
            pass  # Accept all versions
        elif filter_scope == "minor":
            if sem[0] != base[0]:
                continue  # Skip versions with different major component
        elif filter_scope == "patch":
            if not (sem[0] == base[0] and sem[1] == base[1]):
                continue  # Skip versions with different major or minor components
        result.append(v)
    return result


def decide_update(current_version: str, candidate_versions: Sequence[str], sort_order: str) -> Optional[str]:
    """Decide whether to update based on current version and filtered candidates.

    Returns the selected new version or None if no update is needed.
    """
    if not candidate_versions:
        return None

    # Sort versions according to sort_order
    sorted_versions = sorted(candidate_versions, key=lambda x: parse_semver(x), reverse=(sort_order == "desc"))
    newest = sorted_versions[0] if sort_order == "desc" else sorted_versions[-1]
    return newest if is_newer(current_version, newest) else None

# ---------------------------------------------------------------------------
# Update logic
# ---------------------------------------------------------------------------
def update_applications(applications: List[Dict[str, str]], filter_scope: str, sort_order: str) -> List[Dict[str, str]]:
    """Mutate each application record in-place if a newer version exists in scope.

    applications: list of {"name": str, "version": str}
    returns same list (for chaining)
    """
    if not applications:
        logger.info("No applications provided")
        return applications

    logger.info(f"Processing {len(applications)} applications (scope={filter_scope}, order={sort_order})...")
    start_time = datetime.now()
    updated_count = 0

    for app in applications:
        name = app.get("name", "<unknown>")
        current = app.get("version", "0.0.0")
        logger.info(f"Processing: {name} (current: {current})")

        try:
            all_versions = fetch_app_versions(name)
        except Exception as exc:
            logger.error(f"  Error fetching versions for {name}: {exc}")
            logger.info(f"  Skipping update logic for {name} (keeping version {current})")
            continue

        if not all_versions:
            logger.info("  No versions found")
            continue

        filtered = filter_versions(all_versions, current, filter_scope)
        logger.info(f"  Filtered versions: {filtered}")

        if not filtered:
            logger.info("  No candidate versions in scope")
            continue

        new_version = decide_update(current, filtered, sort_order)
        if not new_version:
            logger.info("  Up to date")
            continue

        app["version"] = new_version
        logger.info(f"  Applying update {name}: {current} -> {new_version}")
        updated_count += 1

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"Completed processing in {elapsed:.2f}s. Updated {updated_count}/{len(applications)} applications.")
    return applications

# ---------------------------------------------------------------------------
# Grouped helpers (unchanged semantics)
# ---------------------------------------------------------------------------
def collect_grouped_apps(grouped: Dict[str, List[Dict[str, str]]], groups: Iterable[str] = ("required", "optional")) -> List[Dict[str, str]]:
    """Collect applications from specified groups into a flat list."""
    collected: List[Dict[str, str]] = []
    for g in groups:
        items = grouped.get(g, [])
        if isinstance(items, list):
            collected.extend(items)
    return collected


def print_grouped(grouped: Dict[str, List[Dict[str, str]]]) -> None:
    """Print a grouped application structure in a readable format."""
    for g, items in grouped.items():
        logger.info(f"{g}:")
        for app in items:
            logger.info(f"  {app.get('name')}: {app.get('version')}")

# ---------------------------------------------------------------------------
# Process applications from JSON
# ---------------------------------------------------------------------------
def process_applications_json(applications_json: str, filter_scope: str, sort_order: str) -> Union[Dict[str, List[Dict[str, str]]], List[Dict[str, str]], None]:
    """Process applications JSON input and return the updated structure.

    Returns None if processing fails.
    """
    try:
        payload = json.loads(applications_json)
    except json.JSONDecodeError as exc:
        logger.error(f"Invalid applications JSON: {exc}")
        return None

    original_grouped = False
    grouped: Dict[str, List[Dict[str, str]]] = {}
    flat: List[Dict[str, str]] = []

    if isinstance(payload, dict):
        # assume grouped structure
        for key, val in payload.items():
            if not isinstance(val, list):
                logger.error(f"Group '{key}' must be a list")
                return None
            group_items: List[Dict[str, str]] = []
            for idx, item in enumerate(val):
                if not (isinstance(item, dict) and 'name' in item and 'version' in item):
                    logger.error(f"Invalid item at {key}[{idx}] (needs name & version)")
                    return None
                group_items.append({"name": str(item['name']), "version": str(item['version'])})
            grouped[key] = group_items
            flat.extend(group_items)
        original_grouped = True
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            if not (isinstance(item, dict) and 'name' in item and 'version' in item):
                logger.error(f"Invalid item at index {idx} (needs name & version)")
                return None
            flat.append({"name": str(item['name']), "version": str(item['version'])})
    else:
        logger.error("Applications JSON must be either a JSON object (grouped) or array (flat)")
        return None

    # Log original applications
    logger.info("Original applications:")
    for app in flat:
        logger.info(f" - {app['name']}: {app['version']}")

    logger.info("=" * 40)
    # Process the applications
    update_applications(flat, filter_scope, sort_order)
    logger.info("=" * 40)

    # Log updated applications
    logger.info("Updated applications:")
    for app in flat:
        logger.info(f" - {app['name']}: {app['version']}")

    # Return in the original shape
    if original_grouped:
        return grouped
    return flat

# ---------------------------------------------------------------------------
# Command line argument parsing
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Update application versions based on FAR')
    parser.add_argument('--filter-scope', choices=['major', 'minor', 'patch'], default=FILTER_SCOPE,
                        help=f'Scope of update consideration: major/minor/patch (default: {FILTER_SCOPE})')
    parser.add_argument('--sort-order', choices=['asc', 'desc'], default=SORT_ORDER,
                        help=f'Sort order when evaluating versions (default: {SORT_ORDER})')
    parser.add_argument('--data', type=str, help='JSON string containing application data')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default=LOG_LEVEL,
                        help=f'Logging verbosity level (default: {LOG_LEVEL})')
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
        log_level = args.log_level.upper()

        # Set log level based on argument
        logger.setLevel(getattr(logging, log_level, logging.INFO))

        validate_configuration(filter_scope, sort_order)

        # Check for command line data
        applications_json = None
        if args.data:
            applications_json = args.data
        else:
            applications_json = os.getenv("APPLICATIONS_JSON")

        # If no data provided, exit with error
        if not applications_json:
            logger.error("No application data provided. Use --data argument or APPLICATIONS_JSON environment variable.")
            return 1

        # Process the applications
        output_obj = process_applications_json(applications_json, filter_scope, sort_order)
        if output_obj is None:
            return 1

        # Serialize the updated applications
        serialized = json.dumps(output_obj, separators=(",", ":"), sort_keys=True)

        # Write to GitHub outputs if running in GitHub Actions
        gh_output = os.getenv("GITHUB_OUTPUT")
        if gh_output:
            try:
                with open(gh_output, "a", encoding="utf-8") as fh:
                    fh.write(f"updated-applications={serialized}\n")
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
