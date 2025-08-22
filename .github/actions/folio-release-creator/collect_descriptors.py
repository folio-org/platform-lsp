#!/usr/bin/env python3
"""
Collect application descriptors from FAR API based on platform-descriptor.json
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional
import concurrent.futures
import time


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


def fetch_application_descriptor(far_url: str, app_name: str, app_version: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
  """Fetch application descriptor from FAR API with timeout and error handling."""
  # Construct the API URL with query parameters
  base_url = f"{far_url}/applications/{app_name}-{app_version}"
  params = {'full': 'true'}
  url = f"{base_url}?{urllib.parse.urlencode(params)}"

  try:
    print(f"Fetching {app_name}-{app_version} from {url}")

    # Create request with timeout
    request = urllib.request.Request(url)
    request.add_header('User-Agent', 'FOLIO-Release-Creator/1.0')
    
    with urllib.request.urlopen(request, timeout=timeout) as response:
      if response.status != 200:
        raise Exception(f"HTTP {response.status}")

      data = json.loads(response.read().decode('utf-8'))
      return data

  except Exception as e:
    print(f"::error::Failed to fetch application descriptor for {app_name}-{app_version}: {e}")
    return None


def fetch_multiple_descriptors(far_url: str, applications: List[Dict[str, str]], max_workers: int = 5) -> List[tuple]:
  """Fetch multiple application descriptors concurrently."""
  results = []
  
  with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    # Submit all requests
    future_to_app = {
      executor.submit(fetch_application_descriptor, far_url, app['name'], app['version']): app
      for app in applications
    }
    
    # Collect results as they complete
    for future in concurrent.futures.as_completed(future_to_app):
      app = future_to_app[future]
      try:
        descriptor = future.result()
        results.append((app, descriptor))
      except Exception as e:
        print(f"::error::Unexpected error for {app['name']}-{app['version']}: {e}")
        results.append((app, None))
  
  return results


def collect_descriptors(platform_descriptor_path: str, far_url: str, output_dir: str = "application-descriptors"):
  """Main function to collect all application descriptors with concurrent processing."""
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
    print("::endgroup::")
    return

  print(f"Found {len(all_applications)} applications to fetch")

  # Fetch descriptors concurrently
  start_time = time.time()
  results = fetch_multiple_descriptors(far_url, all_applications)
  fetch_time = time.time() - start_time

  # Process results
  successful_fetches = 0
  failed_fetches = 0

  for app, descriptor in results:
    app_name = app['name']
    app_version = app['version']
    
    if descriptor:
      # Save descriptor to file with name-version.json format
      output_file = output_path / f"{app_name}-{app_version}.json"
      
      try:
        with open(output_file, 'w') as f:
          json.dump(descriptor, f, indent=2, separators=(',', ': '))
        
        print(f"✅ Created {output_file}")
        successful_fetches += 1
      except IOError as e:
        print(f"::error::Failed to write {output_file}: {e}")
        failed_fetches += 1
    else:
      print(f"❌ Failed to fetch {app_name}-{app_version}")
      failed_fetches += 1

  print(f"Successfully collected {successful_fetches} application descriptors in {fetch_time:.1f}s")

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
