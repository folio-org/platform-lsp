#!/usr/bin/env python3

import argparse
import json
import sys


def parse_arguments():
  """Parse command line arguments."""
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


def convert_module_name(module_name):
  """Convert 'folio_module-name' to '@folio/module-name' format."""
  if module_name.startswith("folio_"):
    return f"@folio/{module_name[6:]}"
  return module_name


def parse_version(version):
  """Parse version string into comparable parts."""
  clean_version = version.lstrip('v^~')
  parts = []

  for part in clean_version.split('.'):
    numeric_part = ''.join(char for char in part if char.isdigit())
    parts.append(int(numeric_part) if numeric_part else 0)

  return parts


def is_version_higher(new_version, old_version):
  """Check if new_version is higher than old_version."""
  new_parts = parse_version(new_version)
  old_parts = parse_version(old_version)

  # Pad shorter version with zeros
  max_len = max(len(new_parts), len(old_parts))
  new_parts.extend([0] * (max_len - len(new_parts)))
  old_parts.extend([0] * (max_len - len(old_parts)))

  return new_parts > old_parts


def load_json_safely(json_string, description):
  """Load JSON string with error handling."""
  try:
    print(json_string)
    return json.loads(json_string)
  except json.JSONDecodeError as e:
    print(f"Error: Invalid {description} JSON - {e}", file=sys.stderr)
    sys.exit(1)


def validate_module(module):
  """Validate module has required fields."""
  if not isinstance(module, dict):
    return False
  return "name" in module and "version" in module


def update_dependencies(package_json, ui_modules):
  """Update package.json dependencies based on UI modules."""
  if "dependencies" not in package_json:
    package_json["dependencies"] = {}

  updated_modules = []
  not_found_modules = {}

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

    # Update the dependency
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


def save_results(output_file, package_json, updated_modules, not_found_modules):
  """Save results to output file."""
  structured_output = {
    "package-json": json.dumps(package_json, indent=2, sort_keys=True),
    "updated-ui-report": updated_modules,
    "not-found-ui-report": not_found_modules
  }

  try:
    with open(output_file, 'w', encoding='utf-8') as f:
      json.dump(structured_output, f, indent=2, ensure_ascii=False)
  except IOError as e:
    print(f"Error: Cannot write to output file {output_file} - {e}", file=sys.stderr)
    sys.exit(1)


def main():
  """Main function to process arguments and update package.json."""
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

  # Exit with appropriate code for CI/CD
  if updated_modules:
    print("Dependencies were updated")
    sys.exit(0)
  else:
    print("No dependencies were updated")
    sys.exit(0)


if __name__ == "__main__":
  main()
