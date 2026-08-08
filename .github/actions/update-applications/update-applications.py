#!/usr/bin/env python3
"""
Update application versions based on entries in the FOLIO Application Registry (FAR).

Every entry resolves to the newest version satisfying the constraint declared in the
descriptor template, or the run fails. The descriptor is a projection of the template,
not a memory of the previous run, so there is no "keep what was there" path: a descriptor
mixing fresh and stale versions is a set no one validated.

The preRelease filter is declared per template entry, exactly as folio-application-generator
reads it from an application template, and drives both the FAR query and the candidate
filtering.
"""

# Removed typing imports to keep script simple and parser-compatible
import os
import re
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
FAR_LIMIT = int(os.getenv("FAR_LIMIT", "500"))              # max records to request
FAR_LATEST = int(os.getenv("FAR_LATEST", "50"))             # FAR 'latest' param (server-side filter)
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))            # HTTP request retries (total attempts = MAX_RETRIES + 1)
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "1.0"))    # Base backoff time in seconds

# ---------------------------------------------------------------------------
# Constraint parsing
# ---------------------------------------------------------------------------
LATEST = 'latest'
BRANCH = 'branch'
# The only source of an entry's scope. The scope travels on the entry itself, next to the
# stem it applies to, so there is no second channel that could disagree with the prefix.
PREFIX_TO_SCOPE = {'^': 'minor', '~': 'patch', '': 'exact', LATEST: LATEST, BRANCH: BRANCH}

# PreReleaseFilter, as folio-application-generator defines it for application templates.
PRE_RELEASE_VALUES = ("false", "true", "only")


# Supported grammar: the keyword `latest`, a `#<branch>` pin, or ^X.Y.Z / ~X.Y.Z / X.Y.Z,
# each with an optional pre-release tag such as ^2.1.0-SNAPSHOT. Full semver ranges
# (>=1.0.0 <2.0.0, 1.x, a || b) are not supported; they must be rejected rather than
# silently misread as an exact pin, which would write the literal range into the descriptor.
#
# Naming: this `latest` is the constraint keyword. FAR's `latest=N` query parameter below is
# unrelated — it caps how many recent versions the server returns.
CONSTRAINT_RE = re.compile(r"^([\^~]?)(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$")

# A branch pin, carried through to the descriptor untouched (RANCHER-2880). Deliberately
# narrower than git's own ref rules:
#   - no '/', because folio-release-creator builds a filename as "<app>-<version>.json"
#     and a slash turns a recoverable fetch failure into an IOError
#   - the (?!\d+\.\d+) lookahead rejects '#2.1.0', which is '^2.1.0' typed with the shift
#     key held. Without it that typo becomes a legal pin: it passes the validator and
#     assert_resolved, and validate-platform then skips it, so the application would go
#     quietly un-updated and unvalidated forever.
# Covers every pin this repository has actually carried: #MODSCHED-72, #RANCHER-3029,
# #RANCHER-3029-R1-2026, #RANCHER-3051-SF, #RANCHER-3051-TR.
BRANCH_RE = re.compile(r"^#(?!\d+\.\d+)(?!.*\.\.)[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")

# What may be written back into the descriptor: a concrete version, never a constraint.
# Disjoint from BRANCH_RE by construction — this one requires a leading digit and '#' is
# not a digit, and '#' is not in its alphabet. That is what makes the alternation in
# assert_resolved safe rather than merely convenient.
RESOLVED_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")


def parse_constraint(version_str):
    """Returns (prefix, base_version). prefix is 'latest', 'branch', '^', '~', or ''.

    For `latest` and `#<branch>` the base is the literal itself rather than an empty string:
    an empty base would trip filter_versions' emptiness guard and turn every entry into a
    hard failure.

    A leading '#' is matched against BRANCH_RE rather than accepted wholesale. This function
    is the only place a malformed constraint is caught, and turning it into a catch-all for
    anything starting with '#' would forfeit that.

    Raises ValueError for anything outside the supported grammar."""
    text = (version_str or "").strip()
    if text.lower() == LATEST:
        return LATEST, LATEST
    if text.startswith("#"):
        if not BRANCH_RE.match(text):
            raise ValueError(
                "Invalid branch pin '%s'. Expected #<branch> using letters, digits, '.', "
                "'-' or '_'; no slashes, and not a bare version." % version_str
            )
        return BRANCH, text
    match = CONSTRAINT_RE.match(text)
    if not match:
        raise ValueError(
            "Unsupported version constraint '%s'. Expected 'latest', '#<branch>', ^X.Y.Z, "
            "~X.Y.Z or X.Y.Z, optionally with a pre-release tag." % version_str
        )
    return match.group(1), match.group(2)

# ---------------------------------------------------------------------------
# Version helpers. Non-numeric segments -> 0.
# ---------------------------------------------------------------------------
def parse_version(version):
    """Return (major, minor, patch, is_release, build).

    A pre-release build such as 2.1.0-SNAPSHOT.100200000011364 ranks below the matching
    2.1.0 release and above any lower build of the same base version. A trailing segment
    that is not numeric (feature builds carry a commit hash) ranks as build 0, so such a
    build never outranks a numbered one.
    """
    base, sep, suffix = (version or "0").strip().partition("-")
    nums = []
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


def matches_pre_release(version, pre_release):
    """Apply the PreReleaseFilter semantics to a single version."""
    is_release = parse_version(version)[3] == 1
    if pre_release == "false":
        return is_release
    if pre_release == "only":
        return not is_release
    return True

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
def fetch_app_versions(app_name, pre_release):
    # pre_release is part of the cache key: two template entries for the same application
    # may declare different channels, and a name-only key would serve the first one's
    # answer to the second.
    params = {
        "limit": str(FAR_LIMIT),
        "appName": app_name,
        "preRelease": pre_release,
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
def filter_versions(versions, base_version, scope, pre_release="false"):
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
        raise ValueError("Unsupported scope '%s'. Expected minor, patch or %s." % (scope, LATEST))
    if not versions or not base_version:
        return []
    base = parse_version(base_version)
    result = []
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
# Update logic
# ---------------------------------------------------------------------------
def update_applications(applications):
    """Resolve every application to the newest version satisfying its constraint.

    Each entry carries everything needed to resolve it: the stem in 'version', the window in
    'scope' and the channel in 'preRelease'. Both of the latter are popped here, so what
    leaves this function is {name, version} — see assert_resolved.

    Raises on the first entry that cannot be resolved. A FAR outage, an empty response and
    an all-out-of-scope response are equally a reason to stop: continuing would write a
    descriptor where one application lags behind forty others, which fails validation
    downstream and is harder to diagnose there than a failed run here.
    """
    if not applications:
        logger.info("No applications provided")
        return applications
    logger.info("Processing %s applications..." % len(applications))
    start_time = datetime.now()
    for app in applications:
        name = app.get("name", "<unknown>")
        stem = app.get("version", "0.0.0")
        # Popped before the exact-pin `continue` below: an entry that skips the query must
        # still leave here clean, or the leftover key reaches platform-descriptor.json.
        pre_release = app.pop("preRelease", "false")
        if "scope" not in app:
            raise RuntimeError("Application '%s' reached the resolver without a scope." % name)
        scope = app.pop("scope")
        if scope == 'exact':
            logger.info("Processing: %s (pinned: %s) - exact pin, skipping query" % (name, stem))
            continue
        if scope == BRANCH:
            # The literal is carried into the descriptor untouched; kitfox's
            # validate-application resolves it from the branch's application.lock.json.
            # RANCHER-3070 will turn this skip into a resolution to the branch's build.
            logger.info("Processing: %s (branch-pinned: %s) - skipping FAR query" % (name, stem))
            continue
        logger.info("Processing: %s (constraint: %s, scope: %s, preRelease: %s)"
                    % (name, stem, scope, pre_release))
        all_versions = fetch_app_versions(name, pre_release)
        filtered = filter_versions(all_versions, stem, scope, pre_release)
        logger.info("  Filtered versions: %s" % filtered)
        if not filtered:
            raise RuntimeError(
                "No version of application '%s' satisfies constraint '%s' (scope=%s, "
                "preRelease=%s) in FAR." % (name, stem, scope, pre_release)
            )
        new_version = max(filtered, key=parse_version)
        logger.info("  Resolved %s: %s" % (name, new_version))
        app["version"] = new_version
    assert_resolved(applications, "application")
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("Completed processing in %.2fs. Resolved %s applications." % (elapsed, len(applications)))
    return applications


def assert_resolved(entries, kind):
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
        name = entry.get("name", "<unknown>")
        extra = set(entry) - {"name", "version"}
        if extra:
            raise RuntimeError(
                "Refusing to emit %s '%s' with working keys still attached: %s."
                % (kind, name, ", ".join(sorted(extra)))
            )
        # Two named patterns rather than one widened pattern: a single regex admitting '#'
        # would read as "a version may contain '#'", which is the wrong invariant. A branch
        # pin is a deliberate, separate shape — not a laxer version.
        version = str(entry.get("version", ""))
        if not (RESOLVED_VERSION_RE.match(version) or BRANCH_RE.match(version)):
            raise RuntimeError(
                "Refusing to emit %s '%s' with unresolved version '%s'." % (kind, name, version)
            )

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
def normalize_entry(item):
    """Turn a raw template entry into a resolvable one; drop everything else.

    The constraint is split here into the stem it anchors on and the window it opens, and
    both stay on the entry: 'version' holds the stem, 'scope' the window. Keeping them
    together is what removes the need for a name-keyed side map — which also means the same
    application appearing in two groups gets its own scope in each.
    """
    name = str(item['name'])
    try:
        prefix, base_version = parse_constraint(str(item['version']))
    except ValueError as exc:
        raise ValueError("%s: %s" % (name, exc))
    entry = {"name": name, "version": base_version, "scope": PREFIX_TO_SCOPE[prefix]}
    pre_release = str(item.get('preRelease', 'false')).strip().lower() or 'false'
    if pre_release not in PRE_RELEASE_VALUES:
        raise ValueError(
            "Invalid preRelease '%s' for %s. Allowed: %s"
            % (item.get('preRelease'), name, ', '.join(PRE_RELEASE_VALUES))
        )
    entry['preRelease'] = pre_release
    return entry


def process_applications_json(applications_json):
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
                try:
                    group_items.append(normalize_entry(item))
                except ValueError as exc:
                    logger.error("Invalid item at %s[%s]: %s" % (key, idx, exc))
                    return None
            grouped[key] = group_items
            flat.extend(group_items)
        original_grouped = True
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            if not (isinstance(item, dict) and 'name' in item and 'version' in item):
                logger.error("Invalid item at index %s (needs name & version)" % idx)
                return None
            try:
                flat.append(normalize_entry(item))
            except ValueError as exc:
                logger.error("Invalid item at index %s: %s" % (idx, exc))
                return None
    else:
        logger.error("Applications JSON must be either a JSON object (grouped) or array (flat)")
        return None
    logger.info("Template constraints:")
    for app in flat:
        logger.info(" - %s: %s (scope: %s, preRelease: %s)"
                    % (app['name'], app['version'], app['scope'], app['preRelease']))
    logger.info("=" * 40)
    # flat and grouped hold the same dict objects, so resolving through flat cleans both views.
    update_applications(flat)
    logger.info("=" * 40)
    logger.info("Resolved applications:")
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
        log_level = args.log_level.upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        applications_json = args.data or os.getenv("APPLICATIONS_JSON")
        if not applications_json:
            logger.error("No application data provided. Use --data argument or APPLICATIONS_JSON environment variable.")
            return 1
        output_obj = process_applications_json(applications_json)
        if output_obj is None:
            return 1
        serialized = json.dumps(output_obj, separators=(",", ":"))  # removed sort_keys=True to preserve original object key order
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
