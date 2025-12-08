"""
Main LTspice parser class.

Handles reading and parsing LTspice .asc files and coordinates
netlist generation.
"""

import pyparsing as pp
import matplotlib.pyplot as plt
import lcapy

from .nodes import NodeManager
from .netlist import NetlistGenerator


# Define pyparsing grammar for LTspice format
integer = pp.Word(pp.nums).setParseAction(lambda t: int(t[0]))
signed_integer = pp.Combine(pp.Optional(pp.Literal("-")) + pp.Word(pp.nums)).setParseAction(
    lambda t: int(t[0])
)
real = pp.Combine(
    pp.Optional(pp.Literal("-"))
    + pp.Word(pp.nums)
    + pp.Optional(pp.Literal(".") + pp.Optional(pp.Word(pp.nums)))
).setParseAction(lambda t: float(t[0]))

wire = pp.Literal("WIRE").suppress() + signed_integer + signed_integer + signed_integer + signed_integer

symbol = (
    pp.Literal("SYMBOL")
    + pp.Word(pp.alphanums + "/_")
    + signed_integer
    + signed_integer
    + pp.Regex(r"R\d{0,3}")  # Match R, R0, R90, R180, R270 as single token
)

flag = pp.Literal("FLAG") + signed_integer + signed_integer + pp.Word(pp.alphanums + "+-_")

symattr = pp.Literal("SYMATTR") + pp.Word(pp.alphanums) + pp.restOfLine

window = pp.Literal("WINDOW") + integer + integer + integer + pp.restOfLine

text = pp.Literal("TEXT") + signed_integer + signed_integer + pp.restOfLine


class LTspice:
    """Main class for parsing and processing LTspice files."""

    def __init__(self):
        """Initialize LTspice parser."""
        self.filename = None
        self.contents = None
        self.parsed = None
        self.node_manager = NodeManager()
        self.component_matcher = None

    @property
    def nodes(self):
        """Get nodes dictionary."""
        return self.node_manager.nodes

    @nodes.setter
    def nodes(self, value):
        """Set nodes dictionary."""
        if value is None:
            self.node_manager.nodes = {}
        else:
            self.node_manager.nodes = value

    @property
    def graph(self):
        """Get graph."""
        return self.node_manager.graph

    @graph.setter
    def graph(self, value):
        """Set graph."""
        self.node_manager.graph = value

    def read(self, filename):
        """
        Read an LTspice .asc file, handling multiple possible encodings.

        Tries UTF-8, UTF-16-LE, UTF-16-BE, then latin-1, and picks the first
        decode that looks like a valid LTspice schematic (starts with 'Version').
        """
        self.filename = filename

        # Read raw bytes so we can try multiple encodings
        with open(filename, "rb") as f:
            raw = f.read()

        # Encodings to try, in order of likelihood / preference
        encodings_to_try = ["utf-8", "utf-16-le", "utf-16-be", "latin-1"]

        for enc in encodings_to_try:
            try:
                text = raw.decode(enc)
            except UnicodeDecodeError:
                continue

            # Heuristic: LTspice .asc files start with something like "Version 4"
            stripped = text.lstrip()
            if stripped.startswith("Version") or "Version" in text:
                self.contents = text
                return

        # Last-resort fallback: decode with latin-1 and replace errors
        # (this should never fail and at least gives *some* text)
        self.contents = raw.decode("latin-1", errors="replace")

    def parse(self):
        """
        Parse the LTspice file contents.

        Uses pyparsing to extract circuit elements (wires, symbols, flags, etc.)
        """
        if self.contents is None:
            print("No file loaded. Use read() first.")
            return

        lines = self.contents.split("\n")
        parsed_lines = []

        for line in lines:
            try:
                # Try each grammar rule
                if line.startswith("WIRE"):
                    parsed_lines.append(["WIRE"] + list(wire.parseString(line)))
                elif line.startswith("SYMBOL"):
                    # Start a new symbol group
                    symbol_group = [list(symbol.parseString(line))]
                    parsed_lines.append(symbol_group)
                elif line.startswith("SYMATTR"):
                    # Add to current symbol group
                    if parsed_lines and isinstance(parsed_lines[-1], list):
                        parsed_lines[-1].append(list(symattr.parseString(line)))
                elif line.startswith("FLAG"):
                    # Flags can be standalone or part of symbol
                    flag_data = list(flag.parseString(line))
                    if parsed_lines and isinstance(parsed_lines[-1], list):
                        # Part of previous symbol
                        parsed_lines[-1].append(flag_data)
                    else:
                        # Standalone flag
                        parsed_lines.append([flag_data])
                elif line.startswith("WINDOW"):
                    # Add to current symbol group
                    if parsed_lines and isinstance(parsed_lines[-1], list):
                        parsed_lines[-1].append(list(window.parseString(line)))
                elif line.startswith("TEXT"):
                    # Parse TEXT lines
                    parsed_lines.append(list(text.parseString(line)))
            except pp.ParseException:
                # Skip lines that don't match any pattern
                pass

        self.parsed = parsed_lines

    def print_parsed(self):
        """Print parsed data in readable format."""
        if self.parsed is None:
            print("No parsed data. Use parse() first.")
            return

        for i, line in enumerate(self.parsed):
            print(f"{i}: {line}")

    def sort_nodes(self):
        """Sort nodes dictionary."""
        self.node_manager.sort_nodes()

    def print_nodes(self):
        """Print nodes dictionary."""
        print(self.nodes)

    def plot_nodes2(self):
        """Plot the nodes with labels."""
        miny = 1e6
        maxy = -1e6
        plt.figure(figsize=(14, 6))

        for key in self.nodes:
            x, y = key.split("_")
            node = self.nodes[key]
            xx = int(x)
            yy = int(y)

            miny = min(yy, miny)
            maxy = max(yy, maxy)
            if node == 0:
                plt.plot([xx], [yy], "ok", markersize=3)
                plt.text(xx, yy, "gnd", ha="center", va="top")
            else:
                plt.plot([xx], [yy], "ob", markersize=3)
                plt.text(xx, yy, self.nodes[key], color="blue", ha="right", va="bottom")

        plt.ylim(maxy + 0.1 * (maxy - miny), miny - 0.1 * (maxy - miny))
        plt.show()

    def plot_nodes(self):
        """
        Plot circuit nodes using matplotlib.

        Creates a scatter plot showing node positions and labels.
        """
        if not self.nodes:
            print("No nodes to plot.")
            return

        x_coords = []
        y_coords = []
        labels = []

        for key, value in self.nodes.items():
            # Parse key: "xxxx_yyyy"
            x_str, y_str = key.split("_")
            x = int(x_str)
            y = int(y_str)

            x_coords.append(x)
            y_coords.append(y)
            labels.append(str(value))

        plt.figure(figsize=(12, 8))
        plt.scatter(x_coords, y_coords, s=100, c="blue", alpha=0.6)

        for x, y, label in zip(x_coords, y_coords, labels):
            plt.annotate(label, (x, y), xytext=(5, 5), textcoords="offset points", fontsize=8, color="red")

        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Circuit Nodes")
        plt.grid(True, alpha=0.3)
        plt.gca().invert_yaxis()  # LTspice has Y increasing downward
        plt.show()

    def make_nodes_from_wires(self):
        """Extract nodes from wire definitions."""
        self.node_manager.make_nodes_from_wires(self.parsed)

    def make_nodes_with_net_extraction(self):
        """Create nodes using NetworkX net extraction."""
        self.node_manager.make_nodes_with_net_extraction(self.parsed)

    def make_netlist(
        self,
        use_named_nodes=True,
        include_wire_directions=True,
        minimal=False,
        use_net_extraction=False,
        reorient_rlc=True,
        renumber_nodes=True,
    ):
        """
        Generate netlist from parsed LTspice data.

        Args:
            use_named_nodes: Keep named nodes (True) or convert to numbers (False)
            include_wire_directions: Include direction hints for wires
            minimal: Only include components, no wires
            use_net_extraction: Use NetworkX for net extraction
            reorient_rlc: Reorient R/L/C/W to go right or down only
            renumber_nodes: Renumber nodes sequentially with unique grounds

        Returns:
            str: Generated netlist
        """
        if self.parsed is None:
            self.parse()
            if self.parsed is None:
                return ""

        # Always rebuild nodes from parsed data to ensure fresh coordinate-based keys
        # This is important when make_netlist is called multiple times with different options
        if use_net_extraction:
            self.make_nodes_with_net_extraction()
        else:
            self.make_nodes_from_wires()
            self.sort_nodes()

        # Create netlist generator
        generator = NetlistGenerator(self.nodes, self.parsed)

        # Generate netlist
        self.netlist = generator.generate(
            use_named_nodes=use_named_nodes,
            include_wire_directions=include_wire_directions,
            minimal=minimal,
            use_net_extraction=use_net_extraction,
            reorient_rlc=reorient_rlc,
            renumber_nodes=renumber_nodes,
        )

        # At this point, generator.nodes is the same dict object that came
        # from self.node_manager.nodes, and it has been updated by the
        # renumbering logic. Keep them in sync explicitly:
        self.node_manager.nodes = generator.nodes
        self.nodes = self.node_manager.nodes

        return self.netlist

    def circuit(self):
        """
        Create an lcapy Circuit object from the netlist.

        Returns:
            lcapy.Circuit: Circuit object
        """
        if self.parsed is None:
            self.make_netlist()

        cct = lcapy.Circuit()
        for line in self.netlist.splitlines():
            cct.add(line)

        cct.add(";autoground=true")
        cct.add(";draw_nodes=connections")
        cct.add(";label_nodes=none")
        return cct
