#!/usr/bin/env python3

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple


def parse_arguments() -> argparse.Namespace:
  """Parse command line arguments for the update script."""
  parser = argparse.ArgumentParser(
    description="Update package.json dependencies based on UI modules list"
  )
  parser.add_argument("--package-json", required=True,
                      help="Content of package.json as JSON string")
  parser.add_argument("--ui-modules", required=True,
                      help="List of UI modules as JSON string")
  parser.add_argument("--output-file", required=True,
                      help="Output file path to save the structured JSON result")
  return parser.parse_args()


def convert_module_name(module_name: str) -> str:
  """Convert 'folio_module-name' to '@folio/module-name' format when needed."""
  if module_name.startswith("folio_"):
    return f"@folio/{module_name[6:]}"
  return module_name


def parse_version(version: str) -> List[int]:
  """Parse version string into comparable integer parts, ignoring non-digits."""
  clean_version = version.lstrip('v^~')
  parts: List[int] = []

  for part in clean_version.split('.'):
    numeric_part = ''.join(char for char in part if char.isdigit())
    parts.append(int(numeric_part) if numeric_part else 0)

  return parts


def is_version_higher(new_version: str, old_version: str) -> bool:
  """Return True if new_version is higher than old_version (lexicographically numeric)."""
  new_parts = parse_version(new_version)
  old_parts = parse_version(old_version)

  # Pad shorter version with zeros for fair comparison
  max_len = max(len(new_parts), len(old_parts))
  new_parts.extend([0] * (max_len - len(new_parts)))
  old_parts.extend([0] * (max_len - len(old_parts)))

  return new_parts > old_parts


def load_json_safely(json_string: str, description: str) -> Any:
  """Load JSON string with error handling and exit on failure."""
  try:
    return json.loads(json_string)
  except json.JSONDecodeError as e:
    print(f"Error: Invalid {description} JSON - {e}", file=sys.stderr)
    sys.exit(1)


def validate_module(module: Dict[str, Any]) -> bool:
  """Validate module dict has required 'name' and 'version' fields."""
  if not isinstance(module, dict):
    return False
  return "name" in module and "version" in module


def update_dependencies(package_json: Dict[str, Any], ui_modules: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
  """Update package_json dependencies based on ui_modules list.

  Returns a tuple of (updated_modules_list, not_found_modules_map).
  Business logic unchanged: only upgrade if new version is higher and dependency exists.
  """
  if "dependencies" not in package_json:
    package_json["dependencies"] = {}

  updated_modules: List[Dict[str, Any]] = []
  not_found_modules: Dict[str, str] = {}

  for module in ui_modules:
    if not validate_module(module):
      print(f"Warning: Skipping invalid module: {module}", file=sys.stderr)
      continue

    module_name = module["name"]
    package_name = convert_module_name(module_name)
    new_version = module["version"]

    if package_name not in package_json["dependencies"]:
      print(f"Skipping {package_name}: not in existing dependencies")
      not_found_modules[module_name] = new_version
      continue

    old_version = package_json["dependencies"][package_name]

    if new_version == old_version:
      print(f"Skipping {package_name}: already at version {new_version}")
      continue

    if not is_version_higher(new_version, old_version):
      print(f"Skipping {package_name}: would downgrade from {old_version} to {new_version}")
      continue

    # Perform the update (business logic retained)
    print(f"Updating {package_name}: {old_version} -> {new_version}")
    package_json["dependencies"][package_name] = new_version

    updated_modules.append({
      "name": module_name,
      "change": {
        "old": old_version,
        "new": new_version
      }
    })

  return updated_modules, not_found_modules


def save_results(output_file: str, package_json: Dict[str, Any], updated_modules: List[Dict[str, Any]], not_found_modules: Dict[str, str]) -> None:
  """Persist structured results file consumed by composite action step.

  We intentionally DO NOT sort keys to preserve original ordering and minimize diff noise.
  """
  structured_output = {
    # Preserve original key ordering; pretty-print with indent=2 only.
    "package-json": json.dumps(package_json, indent=2),
    "updated-ui-report": updated_modules,
    "not-found-ui-report": not_found_modules
  }

  try:
    with open(output_file, 'w', encoding='utf-8') as f:
      json.dump(structured_output, f, indent=2, ensure_ascii=False)
  except IOError as e:
    print(f"Error: Cannot write to output file {output_file} - {e}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
  """Entry point: parse args, process upgrade logic, write outputs."""
  args = parse_arguments()

  # Load and validate input data
  package_json = load_json_safely(args.package_json, "package.json")
  ui_modules = load_json_safely(args.ui_modules, "UI modules")

  if not isinstance(ui_modules, list):
    print("Error: UI modules must be a list", file=sys.stderr)
    sys.exit(1)

  # Update dependencies
  updated_modules, not_found_modules = update_dependencies(package_json, ui_modules)

  # Save results
  save_results(args.output_file, package_json, updated_modules, not_found_modules)

  # Print summary
  print(f"Results saved to {args.output_file}")
  print(f"Updated {len(updated_modules)} dependencies")
  print(f"Not found: {len(not_found_modules)} modules")

  # Exit code kept at 0 regardless, to avoid failing workflows when no updates.
  if updated_modules:
    print("Dependencies were updated")
  else:
    print("No dependencies were updated")
  sys.exit(0)


if __name__ == "__main__":
  main()
