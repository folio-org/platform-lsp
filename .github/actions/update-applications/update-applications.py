#!/usr/bin/env python3
"""Print a mock list of applications (hard-coded example).

KISS: No arguments, no JSON parsing. Just iterate and print.
Output format: <group> <name> <version> (tab separated)
"""

DATA = {
    "required": [
        {"name": "app-platform-minimal", "version": "2.0.19"},
        {"name": "app-platform-complete", "version": "2.1.40"},
    ],
    "optional": [
        {"name": "app-acquisitions", "version": "1.0.17"},
        {"name": "app-bulk-edit", "version": "1.0.7"},
        {"name": "app-consortia", "version": "1.2.1"},
        {"name": "app-dcb", "version": "1.1.4"},
        {"name": "app-edge-complete", "version": "2.0.9"},
        {"name": "app-erm-usage", "version": "2.0.3"},
        {"name": "app-fqm", "version": "1.0.11"},
        {"name": "app-marc-migrations", "version": "2.0.1"},
        {"name": "app-oai-pmh", "version": "1.0.2"},
        {"name": "app-inn-reach", "version": "1.0.0"},
        {"name": "app-linked-data", "version": "1.1.6"},
        {"name": "app-reading-room", "version": "2.0.2"},
        {"name": "app-consortia-manager", "version": "1.1.1"},
    ],
}


def main() -> None:
    for group, items in DATA.items():
        for app in items:
            print(f"{group}\t{app.get('name')}\t{app.get('version')}")


if __name__ == "__main__":
    main()
