#!/usr/bin/env python
import json
import sys
from pathlib import Path
from typing import Any


def load_json_file(json_file: Path) -> Any:
    """Load and return data from a JSON file."""
    f = json_file.open()
    return json.load(f)


def parse_via_option(file_str) -> tuple[str, str] | None:
    if ", via option " not in file_str:
        return None
    path_part, option_part = file_str.split(", via option ", 1)
    filename = path_part.strip().rsplit("/", 1)[-1]
    module_name = option_part.strip()
    return filename, module_name


def build_graph(element):
    pass


if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "graph.json"

    data = load_json_file(Path(filepath))

    root = next((el for el in data if el.get("file", "").endswith("/flake.nix")), None)

    if not root:
        print("No element found with a file ending in '/flake.nix'.")
        sys.exit(1)

    print(f"Found flake root: {root['file']}\n")

    graph = build_graph(root)
    print(json.dumps(graph, indent=2))
