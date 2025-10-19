#!/usr/bin/env python3
"""
GitHub Action script to update package.json dependencies based on UI modules list.
Accepts two arguments:
1. package.json content (JSON string)
2. UI modules list (JSON string)
"""

import argparse
import json
import sys
from typing import Dict, Any


def parse_arguments() -> argparse.Namespace:
  """Parse command line arguments."""
  parser = argparse.ArgumentParser(
    description="Update package.json dependencies based on UI modules list"
  )
  parser.add_argument(
    "--package-json",
    help="Content of package.json as JSON string"
  )
  parser.add_argument(
    "--ui-modules",
    help="List of UI modules as JSON string"
  )
  return parser.parse_args()


def convert_ui_module_name(module_name: str) -> str:
  """
  Convert UI module name from 'folio_module-name' format to '@folio/module-name' format.

  Args:
      module_name: Module name in format 'folio_module-name'

  Returns:
      Module name in format '@folio/module-name'
  """
  if module_name.startswith("folio_"):
    # Remove 'folio_' prefix and add '@folio/' prefix
    return f"@folio/{module_name[6:]}"
  return module_name


def update_package_json(package_json_content: str, ui_modules_content: str) -> Dict[str, Any]:
  """
  Update package.json dependencies based on UI modules list.
  Only updates existing dependencies, does not add new ones.

  Args:
      package_json_content: JSON string containing package.json content
      ui_modules_content: JSON string containing list of UI modules

  Returns:
      Updated package.json as dictionary

  Raises:
      json.JSONDecodeError: If input JSON is invalid
      KeyError: If required keys are missing
  """
  try:
    # Parse input JSON strings
    package_json = json.loads(package_json_content)
    ui_modules = json.loads(ui_modules_content)

    # Ensure dependencies section exists
    if "dependencies" not in package_json:
      package_json["dependencies"] = {}

    # Update dependencies based on UI modules (only existing ones)
    for module in ui_modules:
      if not isinstance(module, dict):
        print(f"Warning: Skipping invalid module entry: {module}", file=sys.stderr)
        continue

      if "name" not in module or "version" not in module:
        print(f"Warning: Module missing name or version: {module}", file=sys.stderr)
        continue

      # Convert module name to package.json format
      package_name = convert_ui_module_name(module["name"])
      version = module["version"]

      # Only update if dependency already exists
      if package_name in package_json["dependencies"]:
        old_version = package_json["dependencies"][package_name]
        if old_version != version:
          print(f"Updating {package_name}: {old_version} -> {version}")
          package_json["dependencies"][package_name] = version
      else:
        print(f"Skipping {package_name}: not found in existing dependencies", file=sys.stderr)

    return package_json

  except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input - {e}", file=sys.stderr)
    sys.exit(1)
  except KeyError as e:
    print(f"Error: Missing required key - {e}", file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    print(f"Error: Unexpected error - {e}", file=sys.stderr)
    sys.exit(1)


def main():
  """Main function to process arguments and update package.json."""
  try:
    # Parse command line arguments
    args = parse_arguments()

    # Update package.json based on UI modules
    updated_package_json = update_package_json(args.package_json, args.ui_modules)

    # Output updated package.json as formatted JSON
    print(json.dumps(updated_package_json, indent=2, sort_keys=True))

  except Exception as e:
    print(f"Fatal error: {e}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
  main()
