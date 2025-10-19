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
  parser.add_argument(
    "--output-file",
    required=True,
    help="Output file path to save the structured JSON result"
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


def compare_versions(version1: str, version2: str) -> int:
  """
  Compare two semantic versions.

  Args:
      version1: First version string (e.g., "1.2.3")
      version2: Second version string (e.g., "1.2.4")

  Returns:
      -1 if version1 < version2
       0 if version1 == version2
       1 if version1 > version2
  """
  def normalize_version(version: str) -> list:
    """Convert version string to list of integers for comparison."""
    # Remove common prefixes like 'v' and handle special characters
    clean_version = version.lstrip('v^~')
    # Split by dots and convert to integers, handling non-numeric parts
    parts = []
    for part in clean_version.split('.'):
      try:
        # Extract numeric part only
        numeric_part = ''
        for char in part:
          if char.isdigit():
            numeric_part += char
          else:
            break
        parts.append(int(numeric_part) if numeric_part else 0)
      except ValueError:
        parts.append(0)
    return parts

  v1_parts = normalize_version(version1)
  v2_parts = normalize_version(version2)

  # Pad shorter version with zeros
  max_len = max(len(v1_parts), len(v2_parts))
  v1_parts.extend([0] * (max_len - len(v1_parts)))
  v2_parts.extend([0] * (max_len - len(v2_parts)))

  # Compare each part
  for i in range(max_len):
    if v1_parts[i] < v2_parts[i]:
      return -1
    elif v1_parts[i] > v2_parts[i]:
      return 1

  return 0


def update_package_json(package_json_content: str, ui_modules_content: str) -> Dict[str, Any]:
  """
  Update package.json dependencies based on UI modules list.
  Only updates existing dependencies, does not add new ones.

  Args:
      package_json_content: JSON string containing package.json content
      ui_modules_content: JSON string containing list of UI modules

  Returns:
      Dictionary containing updated package.json and reports

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

    # Initialize reports
    updated_ui_report = []
    not_found_ui_report = {}

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
      module_name = module["name"]

      # Only update if dependency already exists
      if package_name in package_json["dependencies"]:
        old_version = package_json["dependencies"][package_name]

        # Compare versions - only update if new version is higher or equal
        version_comparison = compare_versions(version, old_version)

        if version_comparison > 0:
          # New version is higher
          print(f"Updating {package_name}: {old_version} -> {version}")
          package_json["dependencies"][package_name] = version

          # Add to updated report
          updated_ui_report.append({
            "name": module_name,
            "change": {
              "old": old_version,
              "new": version
            }
          })
        elif version_comparison == 0:
          # Versions are the same
          print(f"Skipping {package_name}: already at version {version}")
        else:
          # New version is lower
          print(f"Skipping {package_name}: would downgrade from {old_version} to {version}", file=sys.stderr)
      else:
        print(f"Skipping {package_name}: not found in existing dependencies", file=sys.stderr)

        # Add to not found report
        not_found_ui_report[module_name] = version

    return {
      "package_json": package_json,
      "updated_ui_report": updated_ui_report,
      "not_found_ui_report": not_found_ui_report
    }

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
    result = update_package_json(args.package_json, args.ui_modules)

    # Create structured output in the required format
    structured_output = {
      "package-json": json.dumps(result["package_json"], indent=2, sort_keys=True),
      "updated-ui-report": result["updated_ui_report"],
      "not-found-ui-report": result["not_found_ui_report"]
    }

    # Save structured output to file
    with open(args.output_file, 'w', encoding='utf-8') as f:
      json.dump(structured_output, f, indent=2, ensure_ascii=False)

    print(f"Results saved to {args.output_file}")
    print(f"Updated {len(result['updated_ui_report'])} dependencies")
    print(f"Not found: {len(result['not_found_ui_report'])} modules")

  except Exception as e:
    print(f"Fatal error: {e}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
  main()
