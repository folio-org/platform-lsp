#!/usr/bin/env python3

import argparse
import concurrent.futures
import json
import subprocess
import sys
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

DEFAULT_FAR_API_URL = "https://far.ci.folio.org"


def _flatten_modules_structure(data: Any) -> List[Dict[str, str]]:
  """Normalize module data.
  Accepts either a list of module dicts or a dict with 'required'/'optional' arrays.
  Raises ValueError for unexpected formats.
  """
  if isinstance(data, dict) and ('required' in data or 'optional' in data):
    modules: List[Dict[str, str]] = []
    if 'required' in data:
      modules.extend(data['required'])
    if 'optional' in data:
      modules.extend(data['optional'])
    return modules
  if isinstance(data, list):
    return data
  raise ValueError("Invalid data format: expected list or dict with 'required'/'optional'")


def load_modules_data(modules_input: str) -> List[Dict[str, str]]:
  """Load modules data from JSON string or file path.
  Tries to parse input first as JSON string; if that fails, as a file path.
  Exits with error (GitHub Actions friendly ::error::) if not retrievable.
  """
  try:
    parsed = json.loads(modules_input)
    return _flatten_modules_structure(parsed)
  except json.JSONDecodeError:
    pass
  except ValueError as e:
    print(f"::error::{e}")
    sys.exit(1)

  try:
    with open(modules_input, 'r') as f:
      parsed = json.load(f)
    return _flatten_modules_structure(parsed)
  except FileNotFoundError as e:
    print(f"::error::Failed to load modules data (file not found): {e}")
    sys.exit(1)
  except json.JSONDecodeError as e:
    print(f"::error::Failed to parse JSON from file: {e}")
    sys.exit(1)
  except ValueError as e:
    print(f"::error::{e}")
    sys.exit(1)


def load_package_json_data(pkg_json_input: str) -> Optional[Dict[str, Any]]:
  """Load package.json from JSON string or file path. Returns None on failure (warning logged)."""
  try:
    return json.loads(pkg_json_input)
  except json.JSONDecodeError:
    pass
  try:
    with open(pkg_json_input, 'r') as f:
      return json.load(f)
  except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"::warning::Failed to load package.json data: {e}")
    return None


def extract_folio_deps(package_json: Dict[str, Any]) -> Dict[str, str]:
  """Return {package_name: version} for all @folio/* entries in package.json dependencies."""
  deps = package_json.get('dependencies', {})
  return {k: v for k, v in deps.items() if k.startswith('@folio/')}


def package_to_folio_module(package_name: str) -> str:
  """Convert npm package name to FAR module name. @folio/foo-bar -> folio_foo-bar"""
  if package_name.startswith('@folio/'):
    return f"folio_{package_name[7:]}"
  return package_name


def folio_module_to_package(module_name: str) -> str:
  """Convert FAR module name to npm package name. folio_foo-bar -> @folio/foo-bar"""
  if module_name.startswith('folio_'):
    return f"@folio/{module_name[6:]}"
  return module_name


def normalize_version(version: str) -> Optional[str]:
  """Strip semver range prefix (^ ~) and return bare version string.
  Returns None for non-parseable formats (git refs, '*', workspace:*, etc.).
  """
  v = version.lstrip('^~ ').strip()
  parts = v.split('.')
  if len(parts) >= 2 and all(p.isdigit() for p in parts[:2]):
    return v
  return None


def find_latest_patch(versions: List[str], current_version: str) -> Optional[str]:
  """Return the latest version with the same major.minor as current_version.
  Only considers versions with numeric patch components (no pre-release suffixes).
  """
  bare = normalize_version(current_version)
  if bare is None:
    return None
  parts = bare.split('.')
  if len(parts) < 2:
    return None
  prefix = f"{parts[0]}.{parts[1]}."
  candidates = [
    v for v in versions
    if v.startswith(prefix) and len(v.split('.')) == 3 and v.split('.')[2].isdigit()
  ]
  if not candidates:
    return None

  def patch_num(v: str) -> int:
    try:
      return int(v.split('.')[2])
    except (IndexError, ValueError):
      return -1

  return max(candidates, key=patch_num)


def npm_view_versions(package_name: str, registry_url: Optional[str] = None, timeout: int = 30) -> Optional[List[str]]:
  """Fetch all published version strings for an npm package via `npm view`.
  Returns None on any failure (warning already logged).
  """
  cmd = ['npm', 'view', package_name, 'versions', '--json']
  if registry_url:
    cmd += ['--registry', registry_url]
  try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
      print(f"::warning::npm view failed for {package_name}: {result.stderr.strip()}")
      return None
    parsed = json.loads(result.stdout.strip())
    # npm returns a plain string (not array) when there is exactly one published version
    if isinstance(parsed, str):
      return [parsed]
    return parsed
  except FileNotFoundError:
    print(f"::warning::npm not found in PATH; skipping version lookup for {package_name}")
    return None
  except subprocess.TimeoutExpired:
    print(f"::warning::npm view timed out for {package_name}")
    return None
  except json.JSONDecodeError as e:
    print(f"::warning::Failed to parse npm view output for {package_name}: {e}")
    return None
  except Exception as e:
    print(f"::warning::Unexpected error fetching npm versions for {package_name}: {e}")
    return None


def fetch_all_npm_versions(
  packages: List[str],
  registry_url: Optional[str],
  max_workers: int = 10,
) -> Dict[str, List[str]]:
  """Concurrent npm view calls for multiple packages. Returns {package_name: [versions]}."""
  results: Dict[str, List[str]] = {}
  with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_pkg = {
      executor.submit(npm_view_versions, pkg, registry_url): pkg
      for pkg in packages
    }
    for future in concurrent.futures.as_completed(future_to_pkg):
      pkg = future_to_pkg[future]
      try:
        versions = future.result()
        if versions is not None:
          results[pkg] = versions
      except Exception as e:
        print(f"::warning::Unexpected error fetching npm versions for {pkg}: {e}")
  return results


def extract_ui_modules(app_descriptors: List[Tuple[Dict[str, str], Optional[Dict[str, Any]]]]) -> List[Dict[str, str]]:
  """Extract uiModules arrays from fetched application descriptors."""
  ui_modules: List[Dict[str, str]] = []
  for app_info, descriptor in app_descriptors:
    if descriptor and 'uiModules' in descriptor:
      modules = descriptor.get('uiModules', [])
      if modules:
        print(f"::debug::Found {len(modules)} UI modules in {app_info.get('name')}-{app_info.get('version')}")
        ui_modules.extend(modules)
  return ui_modules


def fetch_app_descriptor(api_url: str, app_name: str, app_version: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
  """Fetch a single application descriptor from FAR API."""
  url = f"{api_url}/applications/{app_name}-{app_version}?full=false"
  try:
    print(f"::debug::Fetching {app_name}-{app_version} from {url}")
    request = urllib.request.Request(url)
    request.add_header('User-Agent', 'FOLIO-Release-Creator/1.0')
    with urllib.request.urlopen(request, timeout=timeout) as response:
      if response.status != 200:
        raise Exception(f"HTTP {response.status}")
      return json.loads(response.read().decode('utf-8'))
  except Exception as e:
    print(f"::warning::Failed to fetch descriptor for {app_name}-{app_version}: {e}")
    return None


def fetch_all_descriptors(api_url: str, applications: List[Dict[str, str]], max_workers: int = 5) -> List[Tuple[Dict[str, str], Optional[Dict[str, Any]]]]:
  """Fetch multiple application descriptors concurrently."""
  results: List[Tuple[Dict[str, str], Optional[Dict[str, Any]]]] = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_app = {
      executor.submit(fetch_app_descriptor, api_url, app.get('name', ''), app.get('version', '')): app
      for app in applications
    }
    for future in concurrent.futures.as_completed(future_to_app):
      app = future_to_app[future]
      try:
        descriptor = future.result()
        results.append((app, descriptor))
      except Exception as e:
        print(f"::warning::Unexpected error for {app.get('name')}-{app.get('version')}: {e}")
        results.append((app, None))
  return results


def parse_arguments():
  parser = argparse.ArgumentParser(description='Fetch UI modules from FOLIO application descriptors')
  parser.add_argument('--api-url', default=DEFAULT_FAR_API_URL, help=f'FAR API base URL (default: {DEFAULT_FAR_API_URL})')
  parser.add_argument('--modules', help='Modules data as JSON string or path to JSON file')
  parser.add_argument('--output-file', help='Path to output file for UI modules JSON data')
  parser.add_argument('--package-json', default=None,
                      help='package.json content as JSON string or file path; enables npm validation and fallback')
  parser.add_argument('--npm-registry-url', default=None,
                      help='npm registry URL override passed as --registry to npm CLI (defaults to npm built-in)')
  return parser.parse_args()


def main():
  args = parse_arguments()

  if not args.modules:
    print("::error::Modules data is required. Provide via --modules argument.")
    sys.exit(1)

  modules = load_modules_data(args.modules)
  print(f"::notice::Processing {len(modules)} applications for UI modules")

  descriptors = fetch_all_descriptors(args.api_url, modules)
  ui_modules = extract_ui_modules(descriptors)

  if args.package_json:
    pkg_json = load_package_json_data(args.package_json)
    if pkg_json:
      folio_deps = extract_folio_deps(pkg_json)
      if folio_deps:
        registry_url = args.npm_registry_url or None
        print(f"::notice::Querying npm for {len(folio_deps)} @folio/* package(s)")
        npm_versions = fetch_all_npm_versions(list(folio_deps.keys()), registry_url)

        # Validate FAR-covered modules: ensure each FAR-declared version exists on npm.
        # If a version is missing from npm, fall back to the latest patch within the
        # same major.minor as the current package.json version.
        far_module_names = {m['name'] for m in ui_modules}
        for module in ui_modules:
          pkg = folio_module_to_package(module['name'])
          if pkg not in folio_deps:
            continue
          versions = npm_versions.get(pkg)
          if versions is None:
            print(f"::warning::Could not validate {module['name']}@{module['version']} on npm (fetch failed)")
            continue
          if module['version'] not in versions:
            fallback = find_latest_patch(versions, folio_deps[pkg])
            print(
              f"::warning::{module['name']}@{module['version']} (from FAR) not found on npm; "
              f"falling back to {fallback}"
            )
            if fallback:
              module['version'] = fallback

        # npm fallback: cover gap packages absent from any FAR uiModule
        for pkg, current_ver in folio_deps.items():
          if package_to_folio_module(pkg) in far_module_names:
            continue
          versions = npm_versions.get(pkg)
          if versions is None:
            print(f"::warning::Skipping {pkg}: npm versions unavailable")
            continue
          latest = find_latest_patch(versions, current_ver)
          if latest is None:
            print(f"::warning::No npm version matching major.minor of {pkg}@{current_ver}, skipping")
            continue
          print(f"::notice::npm fallback: {pkg} -> {latest} (was: {current_ver})")
          ui_modules.append({"name": package_to_folio_module(pkg), "version": latest, "source": "npm"})

  output_count = len(ui_modules)

  if args.output_file:
    output_data = {"ui_modules": ui_modules, "ui_modules_count": output_count}
    try:
      with open(args.output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
      print(f"::notice::UI modules data written to {args.output_file}")
      print(f"::notice::Found {output_count} UI modules total")
    except Exception as e:
      print(f"::error::Failed to write output file: {e}")
      sys.exit(1)
  else:
    print("\nExtracted UI modules:")
    print(json.dumps(ui_modules, indent=2))
    print(f"\nTotal UI modules found: {output_count}")


if __name__ == '__main__':
  main()