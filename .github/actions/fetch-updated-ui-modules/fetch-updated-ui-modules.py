#!/usr/bin/env python3

import argparse
import concurrent.futures
import json
import sys
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

# NOTE: Business logic preserved. Only structural/clarity improvements.
# Added constant for default FAR API URL (was duplicated in argparse help and action.yml).
DEFAULT_FAR_API_URL = "https://far.ci.folio.org"


def _flatten_modules_structure(data: Any) -> List[Dict[str, str]]:
  """Internal helper to normalize module data.
  Accepts either a list of module dicts or a dict with 'required'/'optional' arrays.
  Returns a flat list. Raises ValueError for unexpected formats.
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
  # Try direct JSON string first
  try:
    parsed = json.loads(modules_input)
    return _flatten_modules_structure(parsed)
  except json.JSONDecodeError:
    pass  # Fall through to file path attempt
  except ValueError as e:
    print(f"::error::{e}")
    sys.exit(1)

  # Attempt file path read
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


def extract_ui_modules(app_descriptors: List[Tuple[Dict[str, str], Optional[Dict[str, Any]]]]) -> List[Dict[str, str]]:
  """Extract UI modules arrays from fetched application descriptors.
  Descriptor entries that lack uiModules are skipped. Collects all modules flat.
  """
  ui_modules: List[Dict[str, str]] = []
  for app_info, descriptor in app_descriptors:
    if descriptor and 'uiModules' in descriptor:
      modules = descriptor.get('uiModules', [])
      if modules:
        print(f"::debug::Found {len(modules)} UI modules in {app_info.get('name')}-{app_info.get('version')}")
        ui_modules.extend(modules)
  return ui_modules


def fetch_app_descriptor(api_url: str, app_name: str, app_version: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
  """Fetch a single application descriptor from FAR API.
  Returns descriptor JSON dict or None on error (logging warning).
  """
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
  """Fetch multiple application descriptors concurrently.
  Any unexpected exception per future is logged and results in (app, None).
  """
  results: List[Tuple[Dict[str, str], Optional[Dict[str, Any]]]] = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_app = {
      executor.submit(fetch_app_descriptor, api_url, app.get('name'), app.get('version')): app
      for app in applications
    }
    for future in concurrent.futures.as_completed(future_to_app):
      app = future_to_app[future]
      try:
        descriptor = future.result()
        results.append((app, descriptor))
      except Exception as e:  # Defensive; should be rare.
        print(f"::warning::Unexpected error for {app.get('name')}-{app.get('version')}: {e}")
        results.append((app, None))
  return results


def parse_arguments():
  """Parse CLI arguments."""
  parser = argparse.ArgumentParser(description='Fetch UI modules from FOLIO application descriptors')
  parser.add_argument('--api-url', default=DEFAULT_FAR_API_URL, help=f'FAR API base URL (default: {DEFAULT_FAR_API_URL})')
  parser.add_argument('--modules', help='Modules data as JSON string or path to JSON file')
  parser.add_argument('--output-file', help='Path to output file for UI modules JSON data')
  return parser.parse_args()


def main():
  """Entry point coordinating data load, fetch, extraction and output."""
  args = parse_arguments()

  if not args.modules:
    print("::error::Modules data is required. Provide via --modules argument.")
    sys.exit(1)

  modules = load_modules_data(args.modules)
  print(f"::notice::Processing {len(modules)} applications for UI modules")

  descriptors = fetch_all_descriptors(args.api_url, modules)
  ui_modules = extract_ui_modules(descriptors)

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
    # Fallback direct stdout (non-action usage)
    print("\nExtracted UI modules:")
    print(json.dumps(ui_modules, indent=2))
    print(f"\nTotal UI modules found: {output_count}")


if __name__ == "__main__":
  main()
