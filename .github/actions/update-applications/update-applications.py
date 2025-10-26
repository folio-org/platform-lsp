#!/usr/bin/env python3
"""
Update application versions based on entries in the FOLIO Application Registry (FAR).

Resolves newer application versions by consulting the FOLIO Application Registry.
Honors semantic versioning scope (major/minor/patch) and sort order preferences.
"""

# Removed typing imports to keep script simple and parser-compatible
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
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))            # HTTP request retries (total attempts = MAX_RETRIES + 1)
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "1.0"))    # Base backoff time in seconds

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_configuration(filter_scope, sort_order):
    valid_filter_scopes = {"major", "minor", "patch"}
    valid_sort_orders = {"asc", "desc"}
    if filter_scope not in valid_filter_scopes:
        raise ValueError("Invalid filter_scope='" + filter_scope + "'. Allowed: " + str(valid_filter_scopes))
    if sort_order not in valid_sort_orders:
        raise ValueError("Invalid sort_order='" + sort_order + "'. Allowed: " + str(valid_sort_orders))

# ---------------------------------------------------------------------------
# Semver helpers (numeric only). Non-numeric segments -> 0.
# ---------------------------------------------------------------------------
def parse_semver(version):
    parts = (version or "0").split(".")
    nums = []
    for p in parts[:3]:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def is_newer(current, candidate):
    return parse_semver(candidate) > parse_semver(current)

# ---------------------------------------------------------------------------
# HTTP Request with retries
# ---------------------------------------------------------------------------
def with_retries(func):
    def wrapper(*args, **kwargs):
        retries = 0
        last_error = None
        while retries <= MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except requests.RequestException as exc:
                last_error = exc
                if hasattr(exc.response, 'status_code') and exc.response.status_code == 429:
                    retry_after = int(exc.response.headers.get('Retry-After', RETRY_BACKOFF))
                    logger.warning("Rate limited. Waiting %ss before retry." % retry_after)
                    time.sleep(retry_after)
                else:
                    wait_time = RETRY_BACKOFF * (2 ** retries) + (time.time() % 1)
                    if retries < MAX_RETRIES:
                        logger.warning("Request failed: %s. Retrying in %.1fs (%s/%s)" % (exc, wait_time, retries+1, MAX_RETRIES))
                        time.sleep(wait_time)
            retries += 1
        logger.error("Failed after %s retries: %s" % (MAX_RETRIES, last_error))
        raise last_error
    return wrapper

# ---------------------------------------------------------------------------
# FAR version retrieval
# ---------------------------------------------------------------------------
@with_retries
@lru_cache(maxsize=128)
def fetch_app_versions(app_name):
    params = {
        "limit": str(FAR_LIMIT),
        "appName": app_name,
        "preRelease": str(FAR_PRE_RELEASE).lower(),
        "latest": str(FAR_LATEST),
    }
    url = FAR_BASE_URL.rstrip('/') + "/applications"
    logger.debug("Fetching versions for %s from %s" % (app_name, url))
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError:
        logger.warning("Non-JSON response for %s; treating as no versions" % app_name)
        return []
    versions = []
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
    logger.debug("Found %s versions for %s" % (len(versions), app_name))
    return versions

# ---------------------------------------------------------------------------
# Version filtering and decision logic
# ---------------------------------------------------------------------------
def filter_versions(versions, base_version, filter_scope):
    if not versions or not base_version:
        return []
    base = parse_semver(base_version)
    result = []
    for v in versions:
        sem = parse_semver(v)
        if filter_scope == "major":
            pass
        elif filter_scope == "minor":
            if sem[0] != base[0]:
                continue
        elif filter_scope == "patch":
            if not (sem[0] == base[0] and sem[1] == base[1]):
                continue
        result.append(v)
    return result


def decide_update(current_version, candidate_versions, sort_order):
    if not candidate_versions:
        return None
    sorted_versions = sorted(candidate_versions, key=lambda x: parse_semver(x), reverse=(sort_order == "desc"))
    newest = sorted_versions[0] if sort_order == "desc" else sorted_versions[-1]
    return newest if is_newer(current_version, newest) else None

# ---------------------------------------------------------------------------
# Update logic
# ---------------------------------------------------------------------------
def update_applications(applications, filter_scope, sort_order):
    if not applications:
        logger.info("No applications provided")
        return applications
    logger.info("Processing %s applications (scope=%s, order=%s)..." % (len(applications), filter_scope, sort_order))
    start_time = datetime.now()
    updated_count = 0
    for app in applications:
        name = app.get("name", "<unknown>")
        current = app.get("version", "0.0.0")
        logger.info("Processing: %s (current: %s)" % (name, current))
        try:
            all_versions = fetch_app_versions(name)
        except Exception as exc:
            logger.error("  Error fetching versions for %s: %s" % (name, exc))
            logger.info("  Skipping update logic for %s (keeping version %s)" % (name, current))
            continue
        if not all_versions:
            logger.info("  No versions found")
            continue
        filtered = filter_versions(all_versions, current, filter_scope)
        logger.info("  Filtered versions: %s" % filtered)
        if not filtered:
            logger.info("  No candidate versions in scope")
            continue
        new_version = decide_update(current, filtered, sort_order)
        if not new_version:
            logger.info("  Up to date")
            continue
        app["version"] = new_version
        logger.info("  Applying update %s: %s -> %s" % (name, current, new_version))
        updated_count += 1
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("Completed processing in %.2fs. Updated %s/%s applications." % (elapsed, updated_count, len(applications)))
    return applications

# ---------------------------------------------------------------------------
# Grouped helpers
# ---------------------------------------------------------------------------
def collect_grouped_apps(grouped, groups=("required", "optional")):
    collected = []
    for g in groups:
        items = grouped.get(g, [])
        if isinstance(items, list):
            collected.extend(items)
    return collected


def print_grouped(grouped):
    for g, items in grouped.items():
        logger.info(g + ":")
        for app in items:
            logger.info("  %s: %s" % (app.get('name'), app.get('version')))

# ---------------------------------------------------------------------------
# Process applications from JSON
# ---------------------------------------------------------------------------
def process_applications_json(applications_json, filter_scope, sort_order):
    try:
        payload = json.loads(applications_json)
    except json.JSONDecodeError as exc:
        logger.error("Invalid applications JSON: %s" % exc)
        return None
    original_grouped = False
    grouped = {}
    flat = []
    if isinstance(payload, dict):
        for key, val in payload.items():
            if not isinstance(val, list):
                logger.error("Group '%s' must be a list" % key)
                return None
            group_items = []
            for idx, item in enumerate(val):
                if not (isinstance(item, dict) and 'name' in item and 'version' in item):
                    logger.error("Invalid item at %s[%s] (needs name & version)" % (key, idx))
                    return None
                group_items.append({"name": str(item['name']), "version": str(item['version'])})
            grouped[key] = group_items
            flat.extend(group_items)
        original_grouped = True
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            if not (isinstance(item, dict) and 'name' in item and 'version' in item):
                logger.error("Invalid item at index %s (needs name & version)" % idx)
                return None
            flat.append({"name": str(item['name']), "version": str(item['version'])})
    else:
        logger.error("Applications JSON must be either a JSON object (grouped) or array (flat)")
        return None
    logger.info("Original applications:")
    for app in flat:
        logger.info(" - %s: %s" % (app['name'], app['version']))
    logger.info("=" * 40)
    update_applications(flat, filter_scope, sort_order)
    logger.info("=" * 40)
    logger.info("Updated applications:")
    for app in flat:
        logger.info(" - %s: %s" % (app['name'], app['version']))
    if original_grouped:
        return grouped
    return flat

# ---------------------------------------------------------------------------
# Command line argument parsing
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description='Update application versions based on FAR')
    parser.add_argument('--filter-scope', choices=['major', 'minor', 'patch'], default=FILTER_SCOPE,
                        help='Scope of update consideration: major/minor/patch (default: %s)' % FILTER_SCOPE)
    parser.add_argument('--sort-order', choices=['asc', 'desc'], default=SORT_ORDER,
                        help='Sort order when evaluating versions (default: %s)' % SORT_ORDER)
    parser.add_argument('--data', type=str, help='JSON string containing application data')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default=LOG_LEVEL,
                        help='Logging verbosity level (default: %s)' % LOG_LEVEL)
    return parser.parse_args()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    try:
        args = parse_args()
        filter_scope = args.filter_scope.lower()
        sort_order = args.sort_order.lower()
        log_level = args.log_level.upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        validate_configuration(filter_scope, sort_order)
        applications_json = args.data or os.getenv("APPLICATIONS_JSON")
        if not applications_json:
            logger.error("No application data provided. Use --data argument or APPLICATIONS_JSON environment variable.")
            return 1
        output_obj = process_applications_json(applications_json, filter_scope, sort_order)
        if output_obj is None:
            return 1
        serialized = json.dumps(output_obj, separators=(",", ":"), sort_keys=True)
        gh_output = os.getenv("GITHUB_OUTPUT")
        if gh_output:
            try:
                with open(gh_output, "a", encoding="utf-8") as fh:
                    fh.write("updated-applications=" + serialized + "\n")
                logger.info("GitHub output written to " + gh_output)
            except Exception as exc:
                logger.error("Failed writing GITHUB_OUTPUT: %s" % exc)
                return 1
        print(serialized)
        return 0
    except Exception as exc:
        logger.error("Unhandled error: %s" % exc, exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
