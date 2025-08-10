#!/usr/bin/env python3
"""
Collect application descriptors from FAR API based on platform-descriptor.json
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any


def load_platform_descriptor(descriptor_path: str) -> Dict[str, Any]:
  """Load and parse the platform-descriptor.json file."""
  try:
    with open(descriptor_path, 'r') as f:
      return json.load(f)
  except FileNotFoundError:
    print(f"::error::Platform descriptor file not found: {descriptor_path}")
    sys.exit(1)
  except json.JSONDecodeError as e:
    print(f"::error::Invalid JSON in platform descriptor: {e}")
    sys.exit(1)


def fetch_application_descriptor(far_url: str, app_name: str, app_version: str) -> Dict[str, Any]:
  """Fetch application descriptor from FAR API."""
  # Construct the API URL with query parameters
  base_url = f"{far_url}/applications/{app_name}-{app_version}"
  params = {'full': 'true'}
  url = f"{base_url}?{urllib.parse.urlencode(params)}"

  try:
    print(f"Fetching {app_name}-{app_version} from {url}")

    with urllib.request.urlopen(url) as response:
      if response.status != 200:
        raise Exception(f"HTTP {response.status}")

      data = json.loads(response.read().decode('utf-8'))
      return data

  except Exception as e:
    print(f"::error::Failed to fetch application descriptor for {app_name}-{app_version}: {e}")
    return None


def collect_descriptors(platform_descriptor_path: str, far_url: str, output_dir: str = "application-descriptors"):
  """Main function to collect all application descriptors."""
  print("::group::Collecting application descriptors from FAR")

  # Load platform descriptor
  platform_desc = load_platform_descriptor(platform_descriptor_path)

  # Create output directory
  output_path = Path(output_dir)
  output_path.mkdir(exist_ok=True)

  # Collect all applications (required + optional)
  all_applications = []

  if 'applications' in platform_desc:
    if 'required' in platform_desc['applications']:
      all_applications.extend(platform_desc['applications']['required'])
    if 'optional' in platform_desc['applications']:
      all_applications.extend(platform_desc['applications']['optional'])

  if not all_applications:
    print("::warning::No applications found in platform descriptor")
    return

  print(f"Found {len(all_applications)} applications to fetch")

  successful_fetches = 0
  failed_fetches = 0

  # Fetch each application descriptor
  for app in all_applications:
    app_name = app['name']
    app_version = app['version']

    descriptor = fetch_application_descriptor(far_url, app_name, app_version)

    if descriptor:
      # Save descriptor to file with name-version.json format
      output_file = output_path / f"{app_name}-{app_version}.json"
      with open(output_file, 'w') as f:
        json.dump(descriptor, f, indent=2)

      print(f"✅ Created {output_file}")
      successful_fetches += 1
    else:
      print(f"❌ Failed to fetch {app_name}-{app_version}")
      failed_fetches += 1

  print(f"Successfully collected {successful_fetches} application descriptors")

  if failed_fetches > 0:
    print(f"::warning::{failed_fetches} application descriptors failed to fetch")

  print("::endgroup::")

  # Exit with error if any critical fetches failed
  if failed_fetches > 0:
    sys.exit(1)


if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: collect_descriptors.py <platform_descriptor_path> <far_url> [output_dir]")
    sys.exit(1)

  platform_descriptor_path = sys.argv[1]
  far_url = sys.argv[2]
  output_dir = sys.argv[3] if len(sys.argv) > 3 else "application-descriptors"

  collect_descriptors(platform_descriptor_path, far_url, output_dir)
