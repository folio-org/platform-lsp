#!/usr/bin/env python3
"""
Update Eureka components script.

Refactored for clarity (KISS + clean code):
- Centralized constants validation
- Single semver parsing / comparison helpers
- Clear function naming and docstrings
- Separation of concerns (fetch, filter, decide, apply)
- Lightweight structured logging helper
- Backward compatibility: process_components kept as alias
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Iterable, Sequence, Tuple, Optional
import os
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "folio-org"
DOCKER_HUB_ORG = "folioorg"

# Scope of update consideration: major / minor / patch
FILTER_SCOPE = os.getenv("FILTER_SCOPE", "patch").lower()
# Sort order when evaluating versions within filtered scope
SORT_ORDER = os.getenv("SORT_ORDER", "asc").lower()  # asc or desc

_VALID_FILTER_SCOPES = {"major", "minor", "patch"}
_VALID_SORT_ORDERS = {"asc", "desc"}

if FILTER_SCOPE not in _VALID_FILTER_SCOPES:
  raise ValueError(f"Invalid FILTER_SCOPE='{FILTER_SCOPE}'. Allowed: {_VALID_FILTER_SCOPES}")
if SORT_ORDER not in _VALID_SORT_ORDERS:
  raise ValueError(f"Invalid SORT_ORDER='{SORT_ORDER}'. Allowed: {_VALID_SORT_ORDERS}")

# Load environment variables from .env file (optional local usage)
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DOCKER_USERNAME = os.getenv("DOCKER_USERNAME")
DOCKER_PASSWORD = os.getenv("DOCKER_PASSWORD")

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Component:
  name: str
  version: str

  @classmethod
  def from_mapping(cls, data: Dict[str, str]) -> "Component":
    return cls(name=data.get("name", "unknown"), version=data.get("version", "unknown"))

  def to_mapping(self) -> Dict[str, str]:
    return {"name": self.name, "version": self.version}

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
  print(msg)

# ---------------------------------------------------------------------------
# Semver helpers (minimal – numeric only, non-numeric parts treated as 0)
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


def is_newer(a: str, b: str) -> bool:
  """Return True if version b is newer (greater) than version a."""
  return parse_semver(b) > parse_semver(a)

# ---------------------------------------------------------------------------
# External service interactions
# ---------------------------------------------------------------------------

def build_github_headers() -> Dict[str, str]:
  headers = {"Accept": "application/vnd.github+json"}
  if GITHUB_TOKEN:
    headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
  return headers


def fetch_repo_release_tags(repo: str, session: Optional[requests.Session] = None) -> List[str]:
  """Return plain (no leading 'v') tag names for releases in org repository."""
  sess = session or requests.Session()
  repo_url = f"{GITHUB_API_URL}/repos/{ORG_NAME}/{repo}"
  releases_url = f"{repo_url}/releases"
  headers = build_github_headers()

  repo_resp = sess.get(repo_url, headers=headers)
  if repo_resp.status_code != 200:
    raise RuntimeError(f"Repository '{repo}' not found in '{ORG_NAME}'.")

  rel_resp = sess.get(releases_url, headers=headers)
  if rel_resp.status_code != 200:
    raise RuntimeError(f"Failed to fetch releases for '{repo}' (status {rel_resp.status_code}).")

  releases = rel_resp.json() or []
  tags = [r.get("tag_name") for r in releases if r.get("tag_name")]
  # Strip leading v/V
  cleaned = [t[1:] if t and t[0] in ("v", "V") and len(t) > 1 else t for t in tags]
  return cleaned


def docker_hub_auth_token(session: requests.Session) -> Optional[str]:
  if not (DOCKER_USERNAME and DOCKER_PASSWORD):
    return None
  try:
    resp = session.post("https://hub.docker.com/v2/users/login/", json={
      "username": DOCKER_USERNAME,
      "password": DOCKER_PASSWORD
    })
    if resp.status_code == 200:
      return resp.json().get("token")
  except Exception as exc:  # noqa: BLE001
    log(f"  Warning: Docker Hub auth failed: {exc}")
  return None


def docker_image_exists(image: str, version: str, session: Optional[requests.Session] = None) -> bool:
  sess = session or requests.Session()
  headers: Dict[str, str] = {}
  token = docker_hub_auth_token(sess)
  if token:
    headers["Authorization"] = f"Bearer {token}"
  url = f"https://hub.docker.com/v2/repositories/{DOCKER_HUB_ORG}/{image}/tags/{version}"
  try:
    resp = sess.get(url, headers=headers)
    return resp.status_code == 200
  except Exception as exc:  # noqa: BLE001
    log(f"  Warning: Docker Hub request failed: {exc}")
    return False

# ---------------------------------------------------------------------------
# Version filtering logic
# ---------------------------------------------------------------------------

def filter_versions(versions: Sequence[str], base_version: str) -> List[str]:
  """Filter versions by configured FILTER_SCOPE relative to base_version."""
  if not versions or not base_version:
    return []
  base = parse_semver(base_version)
  result: List[str] = []
  for v in versions:
    sem = parse_semver(v)
    if FILTER_SCOPE == "major":
      pass  # all included
    elif FILTER_SCOPE == "minor":
      if sem[0] != base[0]:
        continue
    elif FILTER_SCOPE == "patch":
      if not (sem[0] == base[0] and sem[1] == base[1]):
        continue
    result.append(v)
  result.sort(key=lambda x: parse_semver(x), reverse=(SORT_ORDER == "desc"))
  return result

# ---------------------------------------------------------------------------
# Core update logic
# ---------------------------------------------------------------------------

def decide_update(current_version: str, candidate_versions: Sequence[str]) -> Optional[str]:
  """Return the best newer version (according to sort order) or None if no update."""
  if not candidate_versions:
    return None
  newest = candidate_versions[0] if SORT_ORDER == "desc" else candidate_versions[-1]
  return newest if is_newer(current_version, newest) else None


def apply_component_update(component: Component, new_version: str) -> None:
  """Placeholder for real update side-effects."""
  log(f"  - Applying update {component.name}: {component.version} -> {new_version}")
  # Real implementation would go here (e.g., patching files, committing changes, etc.)


def update_components(raw_components: List[Dict[str, str]]) -> List[Dict[str, str]]:
  """
  Update component versions in-place when a newer release (with existing Docker image) is found.
  Returns the same list (mutated) for convenience.
  """
  if not raw_components:
    log("No components to process")
    return raw_components

  components = [Component.from_mapping(c) for c in raw_components]
  log(f"Processing {len(components)} components (scope={FILTER_SCOPE}, order={SORT_ORDER})...")

  session = requests.Session()

  for comp, mapping in zip(components, raw_components):
    log(f"Processing: {comp.name} (current: {comp.version})")
    try:
      all_tags = fetch_repo_release_tags(comp.name, session=session)
    except Exception as exc:  # noqa: BLE001
      log(f"  Error fetching releases: {exc}. Skipping update logic (keeping current version).")
      continue

    filtered = filter_versions(all_tags, comp.version)
    log(f"  Filtered versions: {filtered}")
    new_version = decide_update(comp.version, filtered)

    if not new_version:
      log("  - Up to date")
      continue

    if not docker_image_exists(comp.name, new_version, session=session):
      log(f"  - Docker image missing for {comp.name}:{new_version}; skipping.")
      continue

    apply_component_update(comp, new_version)
    comp.version = new_version
    mapping["version"] = new_version  # reflect change in original structure
    log(f"  - Updated local mapping to {new_version}")

  return raw_components

# ---------------------------------------------------------------------------
# Backward compatibility wrapper (legacy name)
# ---------------------------------------------------------------------------

def process_components(components: List[Dict[str, str]]) -> List[Dict[str, str]]:  # pragma: no cover - thin wrapper
  return update_components(components)

# ---------------------------------------------------------------------------
# Entry point (demo usage)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
  sample_components = [
    {"name": "folio-kong", "version": "3.9.1"},
    {"name": "folio-keycloak", "version": "26.1.3"},
    {"name": "folio-module-sidecar", "version": "3.0.7"},
    {"name": "mgr-applications", "version": "3.0.1"},
    {"name": "mgr-tenants", "version": "3.0.1"},
    {"name": "mgr-tenant-entitlements", "version": "3.1.0"},
  ]

  log("Original components:")
  for c in sample_components:
    log(f" - {c['name']}: {c['version']}")

  log("=" * 40)
  updated = update_components(sample_components)
  log("=" * 40)

  log("Updated components:")
  for c in updated:
    log(f" - {c['name']}: {c['version']}")
