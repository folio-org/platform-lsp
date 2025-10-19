#!/usr/bin/env python3

import argparse
import concurrent.futures
import json
import sys
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional


def load_modules_data(modules_input: str) -> List[Dict[str, str]]:
  """Load modules data from JSON string or file path."""
  try:
    # Try to parse as JSON string first
    return json.loads(modules_input)
  except json.JSONDecodeError:
    # If that fails, try to read as file path
    try:
      with open(modules_input, 'r') as f:
        return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
      print(f"::error::Failed to load modules data: {e}")
      sys.exit(1)


def extract_ui_modules(app_descriptors: List[tuple]) -> List[Dict[str, str]]:
  """Extract UI modules from application descriptors."""
  ui_modules = []

  for app_info, descriptor in app_descriptors:
    if descriptor and 'uiModules' in descriptor:
      modules = descriptor.get('uiModules', [])
      if modules:
        ui_modules.extend(modules)

  return ui_modules


def fetch_app_descriptor(api_url: str, app_name: str, app_version: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
  """Fetch application descriptor from FAR API."""
  url = f"{api_url}/applications/{app_name}-{app_version}?full=false"

  try:
    print(f"Fetching {app_name}-{app_version} from {url}")

    request = urllib.request.Request(url)
    request.add_header('User-Agent', 'FOLIO-Release-Creator/1.0')

    with urllib.request.urlopen(request, timeout=timeout) as response:
      if response.status != 200:
        raise Exception(f"HTTP {response.status}")

      return json.loads(response.read().decode('utf-8'))

  except Exception as e:
    print(f"::error::Failed to fetch descriptor for {app_name}-{app_version}: {e}")
    return None


def fetch_all_descriptors(api_url: str, applications: List[Dict[str, str]], max_workers: int = 5) -> List[tuple]:
  """Fetch multiple application descriptors concurrently."""
  results = []

  with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_app = {
      executor.submit(fetch_app_descriptor, api_url, app['name'], app['version']): app
      for app in applications
    }

    for future in concurrent.futures.as_completed(future_to_app):
      app = future_to_app[future]
      try:
        descriptor = future.result()
        results.append((app, descriptor))
      except Exception as e:
        print(f"::error::Unexpected error for {app['name']}-{app['version']}: {e}")
        results.append((app, None))

  return results


def parse_arguments():
  """Parse command line arguments."""
  parser = argparse.ArgumentParser(description='Fetch UI modules from FOLIO application descriptors')
  parser.add_argument(
    '--api-url',
    default='https://far.ci.folio.org',
    help='FAR API base URL (default: https://far.ci.folio.org)'
  )
  parser.add_argument(
    '--modules',
    help='Modules data as JSON string or path to JSON file'
  )
  return parser.parse_args()


def main():
  """Main execution function."""
  args = parse_arguments()

  # Load modules data
  if args.modules:
    modules = load_modules_data(args.modules)
  else:
    print("::error::Modules data is required. Provide via --modules argument.")
    sys.exit(1)

  # Fetch descriptors and extract UI modules
  descriptors = fetch_all_descriptors(args.api_url, modules)
  ui_modules = extract_ui_modules(descriptors)

  # Output results
  print("\nExtracted UI modules:")
  print(json.dumps(ui_modules, indent=2))
  print(f"\nTotal UI modules found: {len(ui_modules)}")


if __name__ == "__main__":
  main()
