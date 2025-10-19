# Test data for development and testing purposes


TEST_MODULES = [
  {
    "name": "app-acquisitions",
    "version": "1.0.23"
  },
  {
    "name": "app-bulk-edit",
    "version": "1.0.7"
  },
  {
    "name": "app-consortia",
    "version": "1.2.1"
  },
  {
    "name": "app-dcb",
    "version": "1.1.4"
  },
  {
    "name": "app-edge-complete",
    "version": "2.0.11"
  },
  {
    "name": "app-erm-usage",
    "version": "2.0.3"
  },
  {
    "name": "app-fqm",
    "version": "1.0.12"
  },
  {
    "name": "app-marc-migrations",
    "version": "2.0.3"
  },
  {
    "name": "app-oai-pmh",
    "version": "1.0.2"
  },
  {
    "name": "app-inn-reach",
    "version": "1.0.2"
  },
  {
    "name": "app-linked-data",
    "version": "1.1.6"
  },
  {
    "name": "app-reading-room",
    "version": "2.0.2"
  },
  {
    "name": "app-consortia-manager",
    "version": "1.1.1"
  },
  {
    "name": "app-platform-minimal",
    "version": "2.0.27"
  },
  {
    "name": "app-platform-complete",
    "version": "2.1.46"
  }
]

import concurrent.futures
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional


def extract_ui_modules(descriptors: List[tuple]) -> List[Dict[str, str]]:
    """
    Extract UI modules from a list of application descriptors.

    Args:
        descriptors: List of tuples containing (app_info, descriptor) where
                    app_info has 'name' and 'version', and descriptor contains 'uiModules'

    Returns:
        List of UI module objects, each containing 'id', 'name', and 'version'
    """
    ui_modules = []

    for app_info, descriptor in descriptors:
        # Skip if descriptor is None (failed to fetch)
        if descriptor is None:
            continue

        # Skip if descriptor doesn't have uiModules field
        if 'uiModules' not in descriptor:
            continue

        # Extract and add each UI module
        modules = descriptor.get('uiModules', [])
        if modules:
            ui_modules.extend(modules)

    return ui_modules


def fetch_application_descriptor(far_url: str, app_name: str, app_version: str, timeout: int = 30,
                                 full: str = 'false') -> Optional[Dict[str, Any]]:
  """Fetch application descriptor from FAR API with timeout and error handling."""
  # Construct the API URL with query parameters
  base_url = f"{far_url}/applications/{app_name}-{app_version}"
  params = {'full': full}
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


if __name__ == "__main__":
  far_url = 'https://far.ci.folio.org'

  # Extract UI modules from the descriptors
  ui_modules = extract_ui_modules(fetch_multiple_descriptors(far_url, TEST_MODULES))

  print("\nExtracted UI modules:")
  print(json.dumps(ui_modules, indent=2))
  print(f"\nTotal UI modules found: {len(ui_modules)}")
