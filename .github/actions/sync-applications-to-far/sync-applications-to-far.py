#!/usr/bin/env python3
"""
Sync application descriptors from folio-org GitHub repositories to FAR.

Reads applications from platform-descriptor.json, fetches releases from GitHub,
compares with FAR versions, downloads missing application-descriptor.json artifacts,
and POSTs them to FAR.
"""

import os
import sys
import time
import json
import logging
import argparse
import urllib.request
import urllib.parse
from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from github import Github, GithubException

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("sync-to-far")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DESCRIPTOR_PATH = os.getenv("DESCRIPTOR_PATH", "platform-descriptor.json")
FAR_BASE_URL = os.getenv("FAR_BASE_URL", "https://far.ci.folio.org")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in {"1", "true", "yes"}
APPLICATION_GROUPS = os.getenv("APPLICATION_GROUPS", "required,optional")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "1.0"))
FAR_AUTH_TOKEN = os.getenv("FAR_AUTH_TOKEN", "")

# ---------------------------------------------------------------------------
# Semver helpers
# ---------------------------------------------------------------------------
def parse_semver(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string into tuple of integers."""
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


def normalize_version(version: str) -> str:
    """Normalize version string by removing 'v' prefix."""
    return version.lstrip('vV') if version else version


# ---------------------------------------------------------------------------
# HTTP Request with retries
# ---------------------------------------------------------------------------
def with_retries(func):
    """Decorator to add retry logic with exponential backoff."""
    def wrapper(*args, **kwargs):
        retries = 0
        last_error = Exception("Unknown error")
        while retries <= MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except requests.RequestException as exc:
                last_error = exc
                if hasattr(exc, 'response') and exc.response is not None:
                    if exc.response.status_code == 429:
                        retry_after = int(exc.response.headers.get('Retry-After', RETRY_BACKOFF))
                        logger.warning("Rate limited. Waiting %ss before retry." % retry_after)
                        time.sleep(retry_after)
                    elif 400 <= exc.response.status_code < 500 and exc.response.status_code != 409:
                        # Don't retry client errors except 409 (conflict)
                        raise
                if retries < MAX_RETRIES:
                    wait_time = RETRY_BACKOFF * (2 ** retries) + (time.time() % 1)
                    logger.warning("Request failed: %s. Retrying in %.1fs (%s/%s)" % (exc, wait_time, retries+1, MAX_RETRIES))
                    time.sleep(wait_time)
                retries += 1
        logger.error("Failed after %s retries: %s" % (MAX_RETRIES, last_error))
        raise last_error
    return wrapper


# ---------------------------------------------------------------------------
# Platform descriptor loading
# ---------------------------------------------------------------------------
def load_platform_descriptor(descriptor_path: str) -> Dict[str, Any]:
    """Load and parse the platform-descriptor.json file."""
    try:
        with open(descriptor_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Platform descriptor file not found: %s" % descriptor_path)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in platform descriptor: %s" % exc)
        sys.exit(1)


def collect_applications(descriptor: Dict[str, Any], groups: List[str]) -> List[Dict[str, str]]:
    """Collect applications from specified groups in descriptor."""
    apps = []
    applications_section = descriptor.get('applications', {})
    
    for group in groups:
        group_apps = applications_section.get(group, [])
        if isinstance(group_apps, list):
            for app in group_apps:
                if isinstance(app, dict) and 'name' in app and 'version' in app:
                    apps.append({
                        'name': str(app['name']),
                        'version': str(app['version'])
                    })
                else:
                    logger.warning("Invalid application entry in group '%s': %s" % (group, app))
    
    logger.info("Collected %s applications from groups: %s" % (len(apps), ', '.join(groups)))
    return apps


# ---------------------------------------------------------------------------
# GitHub releases fetching
# ---------------------------------------------------------------------------
def fetch_github_releases(app_name: str, github_token: str) -> List[str]:
    """Fetch release versions from GitHub repository."""
    try:
        gh = Github(github_token)
        repo = gh.get_repo("folio-org/%s" % app_name)
        releases = repo.get_releases()
        
        versions = []
        for release in releases:
            tag = release.tag_name
            normalized = normalize_version(tag)
            if normalized:
                versions.append(normalized)
        
        logger.debug("Found %s releases for %s" % (len(versions), app_name))
        return versions
    
    except GithubException as exc:
        if exc.status == 404:
            logger.warning("Repository not found: folio-org/%s" % app_name)
        else:
            logger.error("GitHub API error for %s: %s" % (app_name, exc))
        return []
    except Exception as exc:
        logger.error("Error fetching releases for %s: %s" % (app_name, exc))
        return []


# ---------------------------------------------------------------------------
# FAR version retrieval
# ---------------------------------------------------------------------------
@with_retries
@lru_cache(maxsize=128)
def fetch_far_versions(app_name: str) -> List[str]:
    """Fetch application versions from FAR."""
    params = {
        "limit": "500",
        "appName": app_name,
        "preRelease": "false",
        "latest": "50",
    }
    url = FAR_BASE_URL.rstrip('/') + "/applications"
    logger.debug("Fetching FAR versions for %s from %s" % (app_name, url))
    
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
    
    logger.debug("Found %s versions in FAR for %s" % (len(versions), app_name))
    return versions


# ---------------------------------------------------------------------------
# Version comparison
# ---------------------------------------------------------------------------
def compare_versions(github_versions: List[str], far_versions: List[str]) -> List[str]:
    """Compare GitHub and FAR versions, return missing versions sorted."""
    github_set = set(github_versions)
    far_set = set(far_versions)
    missing = github_set - far_set
    
    # Sort by semantic version
    sorted_missing = sorted(list(missing), key=lambda v: parse_semver(v))
    return sorted_missing


# ---------------------------------------------------------------------------
# Application descriptor download
# ---------------------------------------------------------------------------
def download_application_descriptor(app_name: str, version: str, github_token: str) -> Optional[Dict[str, Any]]:
    """Download application-descriptor.json from GitHub release assets."""
    try:
        gh = Github(github_token)
        repo = gh.get_repo("folio-org/%s" % app_name)
        
        # Try both with and without 'v' prefix
        release = None
        for tag in [version, "v%s" % version]:
            try:
                release = repo.get_release(tag)
                break
            except GithubException:
                continue
        
        if not release:
            logger.warning("Release not found for %s-%s" % (app_name, version))
            return None
        
        # Find application-descriptor.json asset
        descriptor_asset = None
        for asset in release.get_assets():
            if asset.name == "application-descriptor.json":
                descriptor_asset = asset
                break
        
        if not descriptor_asset:
            logger.warning("application-descriptor.json not found in %s-%s release assets" % (app_name, version))
            return None
        
        # Download and parse JSON (with authentication for better rate limits)
        logger.debug("Downloading descriptor from %s" % descriptor_asset.browser_download_url)
        request = urllib.request.Request(descriptor_asset.browser_download_url)
        request.add_header('User-Agent', 'FOLIO-Sync-To-FAR/1.0')
        request.add_header('Authorization', 'token %s' % github_token)
        
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    
    except GithubException as exc:
        logger.error("GitHub API error downloading descriptor for %s-%s: %s" % (app_name, version, exc))
        return None
    except Exception as exc:
        logger.error("Error downloading descriptor for %s-%s: %s" % (app_name, version, exc))
        return None


# ---------------------------------------------------------------------------
# POST to FAR
# ---------------------------------------------------------------------------
@with_retries
def post_to_far(descriptor: Dict[str, Any], dry_run: bool = False) -> Tuple[bool, str]:
    """POST application descriptor to FAR."""
    app_name = descriptor.get('name', 'unknown')
    app_version = descriptor.get('version', 'unknown')
    
    if dry_run:
        logger.info("[DRY RUN] Would POST %s-%s to FAR" % (app_name, app_version))
        logger.debug("[DRY RUN] Descriptor: %s" % json.dumps(descriptor, indent=2))
        return (True, "Dry run - not posted")
    
    url = FAR_BASE_URL.rstrip('/') + "/applications"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'FOLIO-Sync-To-FAR/1.0'
    }
    
    if FAR_AUTH_TOKEN:
        headers['Authorization'] = "Bearer %s" % FAR_AUTH_TOKEN
    
    try:
        response = requests.post(
            url,
            json=descriptor,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 409:
            logger.warning("Application %s-%s already exists in FAR" % (app_name, app_version))
            return (False, "Already exists (409)")
        
        response.raise_for_status()
        logger.info("Successfully posted %s-%s to FAR" % (app_name, app_version))
        return (True, "Success")
    
    except requests.RequestException as exc:
        error_msg = str(exc)
        if hasattr(exc, 'response') and exc.response is not None:
            try:
                error_detail = exc.response.json()
                error_msg = "%s: %s" % (exc, error_detail)
            except:
                error_msg = "%s: %s" % (exc, exc.response.text[:200])
        
        logger.error("Failed to POST %s-%s to FAR: %s" % (app_name, app_version, error_msg))
        raise


# ---------------------------------------------------------------------------
# Process single application
# ---------------------------------------------------------------------------
def process_application(app: Dict[str, str], github_token: str, dry_run: bool) -> Dict[str, Any]:
    """Process a single application: fetch, compare, download, POST."""
    app_name = app['name']
    result = {
        'name': app_name,
        'synced': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }
    
    logger.info("Processing: %s" % app_name)
    
    try:
        # Fetch GitHub releases
        github_versions = fetch_github_releases(app_name, github_token)
        if not github_versions:
            logger.info("  No releases found in GitHub for %s" % app_name)
            return result
        
        # Fetch FAR versions
        far_versions = fetch_far_versions(app_name)
        
        # Compare versions
        missing_versions = compare_versions(github_versions, far_versions)
        
        if not missing_versions:
            logger.info("  All versions already in FAR (%s releases checked)" % len(github_versions))
            result['skipped'] = len(github_versions)
            return result
        
        logger.info("  Missing versions in FAR: %s" % missing_versions)
        
        # Process each missing version
        for version in missing_versions:
            try:
                descriptor = download_application_descriptor(app_name, version, github_token)
                
                if not descriptor:
                    result['failed'] += 1
                    result['errors'].append("Failed to download descriptor for %s-%s" % (app_name, version))
                    continue
                
                success, message = post_to_far(descriptor, dry_run)
                
                if success:
                    result['synced'] += 1
                elif "already exists" in message.lower():
                    result['skipped'] += 1
                else:
                    result['failed'] += 1
                    result['errors'].append("Failed to POST %s-%s: %s" % (app_name, version, message))
            
            except Exception as exc:
                result['failed'] += 1
                result['errors'].append("Error processing %s-%s: %s" % (app_name, version, exc))
                logger.error("  Error processing %s-%s: %s" % (app_name, version, exc))
        
        return result
    
    except Exception as exc:
        logger.error("  Error processing application %s: %s" % (app_name, exc))
        result['errors'].append("Error processing %s: %s" % (app_name, exc))
        return result


# ---------------------------------------------------------------------------
# Sync applications
# ---------------------------------------------------------------------------
def sync_applications(apps: List[Dict[str, str]], github_token: str, dry_run: bool, max_workers: int = 5) -> Dict[str, Any]:
    """Sync multiple applications concurrently."""
    logger.info("=" * 60)
    logger.info("Starting sync for %s applications..." % len(apps))
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_app = {
            executor.submit(process_application, app, github_token, dry_run): app
            for app in apps
        }
        
        for future in as_completed(future_to_app):
            app = future_to_app[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                logger.error("Unexpected error for %s: %s" % (app['name'], exc))
                results.append({
                    'name': app['name'],
                    'synced': 0,
                    'failed': 1,
                    'skipped': 0,
                    'errors': ["Unexpected error: %s" % exc]
                })
    
    # Aggregate results
    total_synced = sum(r['synced'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    total_skipped = sum(r['skipped'] for r in results)
    all_errors = []
    for r in results:
        all_errors.extend(r['errors'])
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    summary = {
        'synced_count': total_synced,
        'failed_count': total_failed,
        'skipped_count': total_skipped,
        'apps_processed': len(results),
        'elapsed_seconds': elapsed,
        'errors': all_errors,
        'details': results
    }
    
    logger.info("=" * 60)
    logger.info("SYNC SUMMARY")
    logger.info("=" * 60)
    logger.info("Applications processed: %s" % len(results))
    logger.info("Descriptors synced: %s" % total_synced)
    logger.info("Descriptors skipped: %s" % total_skipped)
    logger.info("Descriptors failed: %s" % total_failed)
    logger.info("Elapsed time: %.1fs" % elapsed)
    
    if all_errors:
        logger.warning("=" * 60)
        logger.warning("ERRORS (%s)" % len(all_errors))
        logger.warning("=" * 60)
        for error in all_errors[:10]:  # Limit to first 10 errors in log
            logger.warning("  - %s" % error)
        if len(all_errors) > 10:
            logger.warning("  ... and %s more errors" % (len(all_errors) - 10))
    
    logger.info("=" * 60)
    
    return summary


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------
def write_outputs(summary: Dict[str, Any]):
    """Write outputs to GitHub Actions output file and step summary."""
    gh_output = os.getenv("GITHUB_OUTPUT")
    gh_summary = os.getenv("GITHUB_STEP_SUMMARY")
    
    if gh_output:
        try:
            with open(gh_output, "a", encoding="utf-8") as fh:
                fh.write("synced-count=%s\n" % summary['synced_count'])
                fh.write("failed-count=%s\n" % summary['failed_count'])
                fh.write("skipped-count=%s\n" % summary['skipped_count'])
                fh.write("summary=%s\n" % json.dumps(summary, separators=(",", ":")))
            logger.info("GitHub output written to %s" % gh_output)
        except Exception as exc:
            logger.error("Failed writing GITHUB_OUTPUT: %s" % exc)
    
    if gh_summary:
        try:
            with open(gh_summary, "a", encoding="utf-8") as fh:
                fh.write("\n### Sync Results\n\n")
                fh.write("| Metric | Count |\n")
                fh.write("|--------|-------|\n")
                fh.write("| Applications Processed | %s |\n" % summary['apps_processed'])
                fh.write("| Descriptors Synced | %s |\n" % summary['synced_count'])
                fh.write("| Descriptors Skipped | %s |\n" % summary['skipped_count'])
                fh.write("| Descriptors Failed | %s |\n" % summary['failed_count'])
                fh.write("| Elapsed Time | %.1fs |\n" % summary['elapsed_seconds'])
                
                if summary['errors']:
                    fh.write("\n### Errors\n\n")
                    for error in summary['errors'][:20]:  # Limit to 20 errors in summary
                        fh.write("- %s\n" % error)
                    if len(summary['errors']) > 20:
                        fh.write("\n*... and %s more errors*\n" % (len(summary['errors']) - 20))
            
            logger.info("GitHub step summary written to %s" % gh_summary)
        except Exception as exc:
            logger.error("Failed writing GITHUB_STEP_SUMMARY: %s" % exc)


# ---------------------------------------------------------------------------
# Command line argument parsing
# ---------------------------------------------------------------------------
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Sync application descriptors from GitHub to FAR'
    )
    parser.add_argument(
        '--descriptor-path',
        default=DESCRIPTOR_PATH,
        help='Path to platform descriptor file (default: %s)' % DESCRIPTOR_PATH
    )
    parser.add_argument(
        '--far-base-url',
        default=FAR_BASE_URL,
        help='FAR base URL (default: %s)' % FAR_BASE_URL
    )
    parser.add_argument(
        '--github-token',
        default=GITHUB_TOKEN,
        help='GitHub token for API access'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=DRY_RUN,
        help='Preview mode without POSTing to FAR'
    )
    parser.add_argument(
        '--application-groups',
        default=APPLICATION_GROUPS,
        help='Comma-separated list of groups to process (default: %s)' % APPLICATION_GROUPS
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=LOG_LEVEL,
        help='Logging verbosity level (default: %s)' % LOG_LEVEL
    )
    
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    """Main entry point."""
    try:
        args = parse_args()
        
        # Update logger level
        logger.setLevel(getattr(logging, args.log_level.upper(), logging.INFO))
        
        # Validate GitHub token
        if not args.github_token:
            logger.error("GitHub token is required. Set GITHUB_TOKEN or use --github-token")
            return 1
        
        # Load platform descriptor
        descriptor = load_platform_descriptor(args.descriptor_path)
        
        # Collect applications
        groups = [g.strip() for g in args.application_groups.split(',') if g.strip()]
        applications = collect_applications(descriptor, groups)
        
        if not applications:
            logger.warning("No applications found to process")
            write_outputs({
                'synced_count': 0,
                'failed_count': 0,
                'skipped_count': 0,
                'apps_processed': 0,
                'elapsed_seconds': 0.0,
                'errors': [],
                'details': []
            })
            return 0
        
        # Sync applications
        summary = sync_applications(applications, args.github_token, args.dry_run)
        
        # Write outputs
        write_outputs(summary)
        
        # Return error code if there were failures
        if summary['failed_count'] > 0:
            logger.error("Sync completed with %s failures" % summary['failed_count'])
            return 1
        
        logger.info("Sync completed successfully")
        return 0
    
    except Exception as exc:
        logger.error("Unhandled error: %s" % exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
