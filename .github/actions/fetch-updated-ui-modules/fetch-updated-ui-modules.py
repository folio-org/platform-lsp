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
    data = json.loads(modules_input)

    # Handle the case where applications data contains both required and optional
    if isinstance(data, dict) and ('required' in data or 'optional' in data):
      modules = []
      if 'required' in data:
        modules.extend(data['required'])
      if 'optional' in data:
        modules.extend(data['optional'])
      return modules
    elif isinstance(data, list):
      return data
    else:
      raise ValueError("Invalid data format")

  except json.JSONDecodeError:
    # If that fails, try to read as file path
    try:
      with open(modules_input, 'r') as f:
        data = json.load(f)

        # Handle the same format cases for file input
        if isinstance(data, dict) and ('required' in data or 'optional' in data):
          modules = []
          if 'required' in data:
            modules.extend(data['required'])
          if 'optional' in data:
            modules.extend(data['optional'])
          return modules
        elif isinstance(data, list):
          return data
        else:
          raise ValueError("Invalid data format")

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
        print(f"::debug::Found {len(modules)} UI modules in {app_info['name']}-{app_info['version']}")
        ui_modules.extend(modules)

  return ui_modules


def fetch_app_descriptor(api_url: str, app_name: str, app_version: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
  """Fetch application descriptor from FAR API."""
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
        print(f"::warning::Unexpected error for {app['name']}-{app['version']}: {e}")
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
  parser.add_argument(
    '--output-file',
    help='Path to output file for UI modules JSON data'
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

  print(f"::notice::Processing {len(modules)} applications for UI modules")

  # Fetch descriptors and extract UI modules
  descriptors = fetch_all_descriptors(args.api_url, modules)
  ui_modules = extract_ui_modules(descriptors)

  # Output results based on format
  if args.output_file:
    # Write UI modules to file for GitHub Actions consumption
    output_data = {
      "ui_modules": ui_modules,
      "ui_modules_count": len(ui_modules)
    }
    try:
      with open(args.output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
      print(f"::notice::UI modules data written to {args.output_file}")
      print(f"::notice::Found {len(ui_modules)} UI modules total")
    except Exception as e:
      print(f"::error::Failed to write output file: {e}")
      sys.exit(1)
  else:
    # Standard JSON output
    print("\nExtracted UI modules:")
    print(json.dumps(ui_modules, indent=2))
    print(f"\nTotal UI modules found: {len(ui_modules)}")


if __name__ == "__main__":
  main()
