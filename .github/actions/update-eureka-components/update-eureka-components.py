#!/usr/bin/env python3
"""
Update Eureka components script.

Resolves component versions from Docker Hub tags, honouring the constraint and the
preRelease filter declared per entry in the descriptor template.

The descriptor is a projection of the template, not a memory of the previous run: every
entry resolves to the newest version satisfying its constraint, or the run fails. A
partial update would produce a descriptor mixing fresh and stale versions, which is a
set no one validated.

The namespaces searched follow preRelease: false -> folioorg, only -> folioci, true ->
both. Docker Hub orders tags by push time, so candidates are always re-sorted by semver
rather than trusted in the order returned.
"""

from typing import List, Dict, Sequence, Tuple, Optional  # removed unused Any
import os
import re
import sys
import json
import time
import logging
import argparse
from datetime import datetime
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment & logging configuration
# ---------------------------------------------------------------------------
# Load environment variables from .env file (optional local usage)
load_dotenv()
DOCKER_USERNAME = os.getenv("DOCKER_USERNAME")
DOCKER_PASSWORD = os.getenv("DOCKER_PASSWORD")
# LOG_LEVEL is user‑configurable via action input (defaults to INFO if unset/invalid)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Create logger instance early; we'll configure handlers/levels explicitly.
logger = logging.getLogger("eureka-updater")

def configure_logging() -> None:
    """Configure logging based on LOG_LEVEL env var (fallback to INFO)."""
    # Accept common levels; default to INFO if unknown.
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    # basicConfig only affects root handlers if not already configured.
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger.setLevel(level)
    logger.debug(f"Logging configured (level={logging.getLevelName(level)})")

configure_logging()

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
DOCKER_HUB_API = "https://hub.docker.com/v2/repositories"
TAG_PAGE_SIZE = 100
MAX_TAG_PAGES = 10  # 1000 tags; folioci holds ~138 today, folioorg 12-42

RELEASE_ORG = "folioorg"
PRE_RELEASE_ORG = "folioci"

# PreReleaseFilter, as folio-application-generator defines it for application templates.
PRE_RELEASE_VALUES = ("false", "true", "only")
ORGS_BY_PRE_RELEASE = {
    "false": (RELEASE_ORG,),
    "only": (PRE_RELEASE_ORG,),
    "true": (RELEASE_ORG, PRE_RELEASE_ORG),
}

# Retry configuration constants (tunable without altering business logic)
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2
RETRY_INITIAL_WAIT = 1  # seconds

# ---------------------------------------------------------------------------
# Constraint parsing
# ---------------------------------------------------------------------------
LATEST = 'latest'
# The only source of an entry's scope. The scope travels on the entry itself, next to the
# stem it applies to, so there is no second channel that could disagree with the prefix.
PREFIX_TO_SCOPE = {'^': 'minor', '~': 'patch', '': 'exact', LATEST: LATEST}


# See update-applications.py for the supported grammar; kept identical on purpose.
#
# Naming: this `latest` is the constraint keyword. The Docker Hub tag literally named
# `latest` is a separate thing and is discarded in fetch_docker_tags, before filtering.
CONSTRAINT_RE = re.compile(r"^([\^~]?)(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$")

# What may be written back into the descriptor: a concrete version, never a constraint.
RESOLVED_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")


def parse_constraint(version_str: str) -> Tuple[str, str]:
    """Returns (prefix, base_version). prefix is 'latest', '^', '~', or ''.

    For `latest` the base is the keyword itself rather than an empty string: an empty base
    would trip filter_versions' emptiness guard and turn every entry into a hard failure.
    Raises ValueError for anything outside the supported grammar."""
    text = (version_str or "").strip()
    if text.lower() == LATEST:
        return LATEST, LATEST
    if text.startswith("#"):
        raise ValueError(
            f"Branch pin '{version_str}' is not supported for eureka-components. "
            "A #<branch> pin resolves an application descriptor from that branch; components "
            "are Docker images and have no such artifact."
        )
    match = CONSTRAINT_RE.match(text)
    if not match:
        raise ValueError(
            f"Unsupported version constraint '{version_str}'. Expected 'latest', ^X.Y.Z, "
            "~X.Y.Z or X.Y.Z, optionally with a pre-release tag."
        )
    return match.group(1), match.group(2)

# ---------------------------------------------------------------------------
# SemVer helpers (minimal – numeric only, non-numeric parts treated as 0)
# ---------------------------------------------------------------------------
def parse_version(version: str) -> Tuple[int, int, int, int, int]:
    """Return (major, minor, patch, is_release, build).

    A pre-release build such as 4.1.0-SNAPSHOT.2289 ranks below the matching 4.1.0
    release and above any lower build of the same base version. A trailing segment that
    is not numeric ranks as build 0.
    """
    base, sep, suffix = (version or "0").strip().partition("-")
    nums: List[int] = []
    for p in base.split(".")[:3]:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    if not sep:
        return (nums[0], nums[1], nums[2], 1, 0)
    build = 0
    for part in reversed(suffix.split(".")):
        if part.isdigit():
            build = int(part)
            break
    return (nums[0], nums[1], nums[2], 0, build)


# ---------------------------------------------------------------------------
# External service interactions
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
                    retry_after = int(exc.response.headers.get('Retry-After', RETRY_INITIAL_WAIT))
                    logger.warning(f"Rate limited. Waiting {retry_after}s before retry.")
                    time.sleep(retry_after)
                else:
                    # Simple exponential backoff + lightweight jitter
                    wait_time = RETRY_INITIAL_WAIT * (RETRY_BACKOFF_BASE ** retries) + (time.time() % 1)
                    if retries < MAX_RETRIES:
                        logger.warning(
                            f"Request failed: {exc}. Retrying in {wait_time:.1f}s ({retries+1}/{MAX_RETRIES})"
                        )
                        time.sleep(wait_time)
            retries += 1

        logger.error(f"Failed after {MAX_RETRIES} retries: {last_error}")
        raise last_error

    return wrapper


@with_retries
def fetch_docker_tags(org: str, image: str, session: Optional[requests.Session] = None) -> List[str]:
    """Return every tag name for an image, following Docker Hub pagination.

    'latest' is discarded: it is an alias Docker Hub does not resolve for us, and on a
    release namespace it points at the newest push, which is not necessarily the newest
    version (patches to an older line are pushed after a new major).
    """
    sess = session or requests.Session()
    headers: Dict[str, str] = {}
    token = docker_hub_auth_token(sess)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{DOCKER_HUB_API}/{org}/{image}/tags/?page_size={TAG_PAGE_SIZE}"
    names: List[str] = []
    for _ in range(MAX_TAG_PAGES):
        resp = sess.get(url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Failed to list tags for '{org}/{image}' (status {resp.status_code})."
            )
        payload = resp.json() or {}
        names.extend(r["name"] for r in (payload.get("results") or [])
                     if isinstance(r, dict) and r.get("name") and r["name"] != "latest")
        url = payload.get("next")
        if not url:
            break
    else:
        logger.warning(f"  Tag listing for {image} hit the {MAX_TAG_PAGES}-page cap; older tags ignored")

    return names


def docker_hub_auth_token(session: requests.Session) -> Optional[str]:
    """Get Docker Hub auth token if credentials are provided (optional)."""
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



# ---------------------------------------------------------------------------
# Version filtering logic
# ---------------------------------------------------------------------------
def matches_pre_release(version: str, pre_release: str) -> bool:
    """Apply the PreReleaseFilter semantics to a single version."""
    is_release = parse_version(version)[3] == 1
    if pre_release == "false":
        return is_release
    if pre_release == "only":
        return not is_release
    return True


def filter_versions(versions: Sequence[str], base_version: str, scope: str,
                    pre_release: str = "false") -> List[str]:
    """Filter versions to the constraint window and the pre-release channel.

    The window matches how semver4j — the engine behind /applications/validate-descriptors —
    expands the range: ^2.1.0-SNAPSHOT becomes >=2.1.0-SNAPSHOT and <3.0.0-0, so the scope
    supplies the upper bound and base_version the lower one.

    'latest' has no window at all. It short-circuits before any version arithmetic, because
    parse_version('latest') would quietly yield (0, 0, 0, 1, 0) — a zero version tagged as a
    release — and every bound below would then be computed against that.

    The scope whitelist is not decoration: an unrecognised token used to fall past both
    branches below and silently mean "no upper bound", which reads as a licence to jump
    majors. 'exact' never reaches here — those entries are skipped without a query.
    """
    if scope == LATEST:
        return [v for v in versions if matches_pre_release(v, pre_release)]
    if scope not in ("minor", "patch"):
        raise ValueError(f"Unsupported scope '{scope}'. Expected minor, patch or {LATEST}.")
    if not versions or not base_version:
        return []

    base = parse_version(base_version)
    result: List[str] = []

    for v in versions:
        sem = parse_version(v)
        if scope == "minor":
            if sem[0] != base[0]:
                continue
        else:
            if not (sem[0] == base[0] and sem[1] == base[1]):
                continue
        if sem < base:
            continue
        if not matches_pre_release(v, pre_release):
            continue
        result.append(v)

    return result

# ---------------------------------------------------------------------------
# Core update logic
# ---------------------------------------------------------------------------
def update_components(components: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Resolve every component to the newest version satisfying its constraint.

    Each entry carries everything needed to resolve it: the stem in 'version', the window
    in 'scope' and the channel in 'preRelease'. Both of the latter are popped here, so what
    leaves this function is {name, version} — see assert_resolved.

    Raises on the first entry that cannot be resolved — a registry outage, an empty tag
    list and an all-out-of-scope tag list are equally a reason to stop, because writing a
    descriptor where one component lags behind forty others produces a set that was never
    validated. Returns the same list (mutated) for convenience.
    """
    if not components:
        logger.info("No components to process")
        return components

    logger.info(f"Processing {len(components)} components...")
    start_time = datetime.now()
    session = requests.Session()

    for comp in components:
        name = comp.get("name", "unknown")
        stem = comp.get("version", "0.0.0")
        # Popped before the exact-pin `continue` below: an entry that skips the query must
        # still leave here clean, or the leftover key reaches platform-descriptor.json.
        pre_release = comp.pop("preRelease", "false")
        if "scope" not in comp:
            raise RuntimeError(f"Component '{name}' reached the resolver without a scope.")
        scope = comp.pop("scope")
        if scope == 'exact':
            logger.info(f"Processing: {name} (pinned: {stem}) - exact pin, skipping query")
            continue

        orgs = ORGS_BY_PRE_RELEASE[pre_release]
        logger.info(f"Processing: {name} (constraint: {stem}, scope: {scope}, "
                    f"preRelease: {pre_release}, registries: {'/'.join(orgs)})")

        candidates: List[str] = []
        for org in orgs:
            tags = fetch_docker_tags(org, name, session=session)
            logger.debug(f"  {len(tags)} tags in {org}/{name}")
            candidates.extend(tags)

        filtered = filter_versions(candidates, stem, scope, pre_release)
        logger.info(f"  In-scope versions: {filtered}")
        if not filtered:
            raise RuntimeError(
                f"No version of component '{name}' satisfies constraint '{stem}' "
                f"(scope={scope}, preRelease={pre_release}) in {'/'.join(orgs)}."
            )

        # Every candidate is a published tag, so no separate existence check is needed.
        new_version = max(filtered, key=parse_version)
        logger.info(f"  - Resolved {name}: {new_version}")
        comp["version"] = new_version

    assert_resolved(components, "component")
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"Completed processing in {elapsed:.2f}s. Resolved {len(components)} components.")
    return components


def assert_resolved(entries: List[Dict[str, str]], kind: str) -> None:
    """Fail unless every entry is exactly {name, version} holding a concrete version.

    Neither half of this is cosmetic, and this is the only place that sees every entry on
    every path.

    A leaked constraint is not self-healing: written into the descriptor, the next run would
    emit the same constraint the descriptor already holds, report "no changes" and skip
    everything — hourly, forever.

    A leaked working key is worse, because nothing downstream would notice. compare-components
    diffs with jq's `==`, which is key-set sensitive, so an extra key reports "changed" on
    every run; Apply Descriptor Updates then writes the entries verbatim into
    platform-descriptor.json; and validate-platform and the diff report both re-project to
    {name, version}, so validation stays green and the report looks ordinary. One bogus
    version bump and one corrupt commit later the descriptor carries the key on both sides,
    the comparison balances again, and it never fails a second time.
    """
    for entry in entries:
        name = entry.get("name", "unknown")
        extra = set(entry) - {"name", "version"}
        if extra:
            raise RuntimeError(
                f"Refusing to emit {kind} '{name}' with working keys still attached: "
                f"{', '.join(sorted(extra))}."
            )
        version = entry.get("version", "")
        if not RESOLVED_VERSION_RE.match(str(version)):
            raise RuntimeError(
                f"Refusing to emit {kind} '{name}' with unresolved version '{version}'."
            )

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Update Eureka components')
    parser.add_argument('--data', type=str, help='JSON string containing component data')
    return parser.parse_args()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    """Main entry point with proper error handling and return code."""
    try:
        args = parse_args()
        components_data = None
        if args.data:
            try:
                components_data = json.loads(args.data)
            except json.JSONDecodeError as exc:
                logger.error(f"Invalid JSON data provided via --data: {exc}")
                return 1

        if components_data is None:
            logger.error("No component data provided. Use --data argument to provide components.")
            return 1

        if not isinstance(components_data, list):
            raise ValueError("Component data must be a JSON array of objects with name/version")
        for idx, item in enumerate(components_data):
            if not isinstance(item, dict) or "name" not in item or "version" not in item:
                raise ValueError(f"Item at index {idx} must be an object with 'name' and 'version'")

        logger.info("Template constraints:")
        for c in components_data:
            logger.info(f" - {c['name']}: {c['version']} (preRelease: {c.get('preRelease', 'false')})")

        # Split each constraint into the stem it anchors on and the window it opens, and
        # attach both to the entry. The scope stays next to the stem it applies to.
        for comp in components_data:
            try:
                prefix, base_version = parse_constraint(comp['version'])
            except ValueError as exc:
                logger.error(f"Invalid version constraint for {comp.get('name')}: {exc}")
                return 1
            comp['version'] = base_version
            comp['scope'] = PREFIX_TO_SCOPE[prefix]
            pre_release = str(comp.get('preRelease', 'false')).strip().lower() or 'false'
            if pre_release not in PRE_RELEASE_VALUES:
                logger.error(f"Invalid preRelease '{comp.get('preRelease')}' for {comp.get('name')}. "
                             f"Allowed: {', '.join(PRE_RELEASE_VALUES)}")
                return 1
            comp['preRelease'] = pre_release

        logger.info("=" * 40)
        updated = update_components(components_data)
        logger.info("=" * 40)

        logger.info("Resolved components:")
        for c in updated:
            logger.info(f" - {c['name']}: {c['version']}")

        serialized = json.dumps(updated, separators=(",", ":"))  # removed sort_keys=True to preserve key order

        gh_output = os.getenv("GITHUB_OUTPUT")
        if gh_output:
            try:
                with open(gh_output, "a", encoding="utf-8") as fh:
                    fh.write(f"updated-components={serialized}\n")
                logger.debug(f"GitHub output written to {gh_output}")
            except Exception as exc:
                logger.error(f"Failed writing GITHUB_OUTPUT: {exc}")
                return 1

        print(serialized)  # stdout always emits JSON result
        return 0

    except Exception as exc:
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
