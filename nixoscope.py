#!/usr/bin/env python
import argparse
import colorsys
import json
from dataclasses import dataclass, field
from pathlib import Path

import graphviz


@dataclass
class ModuleGraphEdge:
    source: str = field(default_factory=str)
    path: str = field(default_factory=str)
    option: str = field(default_factory=str)

    def __init__(self, raw_module: dict) -> None:
        source_path, _, path_and_option = str(raw_module["file"]).partition("-source")
        self.source = source_path.rsplit("/", 1)[-1]
        path_and_option = path_and_option.removeprefix("/")
        self.path, _, self.option = path_and_option.partition(", via option ")

    def to_dict(self):
        return {"source": self.source, "path": self.path}

    def __eq__(self, other: object):
        if not isinstance(other, ModuleGraphEdge):
            return NotImplemented
        return self.source == other.source and self.path == other.path


@dataclass
class ModuleGraphNode(ModuleGraphEdge):
    imports: list[ModuleGraphEdge] = field(default_factory=list)

    def to_dict(self):
        return (
            super().to_dict()
            | {"imports": [module.to_dict() for module in self.imports]}
            | ({"option": self.option} if self.option else {})
        )

    def __eq__(self, other: object):
        if not isinstance(other, ModuleGraphEdge):
            return NotImplemented
        return self.source == other.source and self.path == other.path


class ModuleGraph:
    modules: dict[tuple[str, str], ModuleGraphNode]

    def __init__(self, raw_modules: list, option_filter: str | None) -> None:
        """Build a ModuleGraph from the loaded JSON data."""
        self.modules = {}
        for raw_module in raw_modules:
            self._process_entry(raw_module, option_filter=option_filter)

    def _process_entry(
        self,
        raw_module: dict,
        option_filter: str | None,
        parent: ModuleGraphNode | None = None,
    ) -> None:
        """Process a single entry from the graph JSON and add it to the ModuleGraph."""
        edge = ModuleGraphEdge(raw_module)

        # Check if flake.nix starting point
        is_flake_entry = edge.path == "flake.nix"
        # Check if option filter should be applied and if this edge matches the option filter
        matches_option_filter = option_filter is None or edge.option.startswith(option_filter)

        if is_flake_entry or matches_option_filter:
            node = self._get_or_create_module(edge)
            if parent and edge != parent:
                self._add_import_to_module(parent, edge)
        else:
            node = parent

        # Always process imports recursively
        imports = raw_module.get("imports", [])
        for imported_entry in imports:
            self._process_entry(imported_entry, option_filter, node)

    def _get_or_create_module(self, edge: ModuleGraphEdge) -> ModuleGraphNode:
        key = (edge.source, edge.path)
        if key not in self.modules:
            node = ModuleGraphNode(edge.source, edge.path, edge.option)
            self.modules[key] = node
        return self.modules[key]

    def _add_import_to_module(self, parent: ModuleGraphNode, edge: ModuleGraphEdge) -> None:
        key = (parent.source, parent.path)
        if edge not in self.modules[key].imports:
            self.modules[key].imports.append(edge)

    def to_json(self) -> str:
        result = [module.to_dict() for module in self.modules.values()]
        return json.dumps(result, indent=2)

    def to_gv(self) -> graphviz.Digraph:
        dot = graphviz.Digraph("ModuleGraph")
        dot.attr("node", shape="box", fontname="Helvetica", style="filled")

        # Add nodes
        for (source, path), node in self.modules.items():
            node_id = f"{source}-{path}"
            label = f"<<B>{path}</B><BR/>{node.option}<BR/><I>{source}</I>>"
            dot.node(name=node_id, label=label, fillcolor=ModuleGraph._color_from_cluster_id(source))

        # Add edges
        for (source, path), node in self.modules.items():
            from_id = f"{source}-{path}"
            for imported_edge in node.imports:
                to_id = f"{imported_edge.source}-{imported_edge.path}"
                dot.edge(from_id, to_id)

        return dot

    @staticmethod
    def _color_from_cluster_id(cluster_id: str) -> str:

        # Hash the string to a number
        n = abs(hash(cluster_id))
        # Use 137 as golden angle to create different colors even if two n are close in range
        hue = (n * 137) % 360
        saturation = 0.5  # not too grey, not too vivid
        lightness = 0.80  # high = washed out / soft
        r, g, b = colorsys.hls_to_rgb(hue / 360.0, lightness, saturation)
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Input module graph from a JSON file.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("graph.json"),
        help="Path to the graph JSON file (default: graph.json)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["gv", "json"],
        default="gv",
        help="Output format (default: gv)",
    )
    parser.add_argument(
        "--option",
        type=str,
        default=None,
        help="Filter by option prefix",
    )

    return parser.parse_args()


def load_json(json_file: Path) -> dict:
    """Load and return data from a JSON file."""
    f = json_file.open()
    return json.load(f)


def main():
    args = parse_args()
    raw_modules = load_json(args.input)

    # Filter data to only handle everything under flake.nix
    raw_modules = [raw_module for raw_module in raw_modules if str(raw_module["file"]).endswith("/flake.nix")]
    graph = ModuleGraph(raw_modules, args.option)

    if args.format == "gv":
        print(graph.to_gv())
    else:
        print(graph.to_json())


if __name__ == "__main__":
    main()
