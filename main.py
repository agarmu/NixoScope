#!/usr/bin/env python

import json
import sys
from pathlib import Path


def load_json_file(json_file: Path) -> dict:
    """Load and return data from a JSON file."""
    f = json_file.open()
    return json.load(f)


def parse_via_option(file_str) -> dict | None:
    if ", via option " not in file_str:
        return None
    path_part, option_part = file_str.split(", via option ", 1)
    return {
        "filename": path_part.strip().rsplit("/", 1)[-1],
        "module_name": option_part.strip(),
    }


def build_graph(node: dict, graph: dict | None = None, parent_module_name: str | None = None) -> dict:
    if graph is None:
        graph = {}

    file_str = node.get("file", "")
    element = parse_via_option(file_str)
    current_module_name = element["module_name"] if element else parent_module_name

    if current_module_name not in graph:
        graph[current_module_name] = {"imports": [], "files": []}

    if element and element["filename"] not in graph[current_module_name]["files"]:
        graph[current_module_name]["files"].append(element["filename"])

    if (
        element
        and parent_module_name
        and parent_module_name != current_module_name
        and current_module_name not in graph[parent_module_name]["imports"]
    ):
        graph[parent_module_name]["imports"].append(current_module_name)

    for child in node.get("imports", []):
        build_graph(child, graph, current_module_name)

    return graph


if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "graph.json"
    data = load_json_file(Path(filepath))
    root = next((el for el in data if el.get("file", "").endswith("/flake.nix")), None)

    if not root:
        print("No element found with a file ending in '/flake.nix'.")
        sys.exit(1)
    print(json.dumps(root, indent=2))

    graph = build_graph(root)  # ty:ignore[invalid-argument-type]
    print(json.dumps(graph, indent=2))
