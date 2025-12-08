"""
Node management for ltparser.

Handles node extraction, sorting, and network analysis.
"""

import networkx as nx
from .components import node_key


class NodeManager:
    """Manages circuit nodes and their extraction from wires."""

    def __init__(self):
        """Initialize node manager."""
        self.nodes = {}
        self.graph = nx.Graph()

    def add_node(self, x, y, name=False):
        """
        Add a node at coordinates (x, y).

        Args:
            x, y: Node coordinates
            name: Optional node name (if False, uses auto-numbering)

        Returns:
            Node identifier (number or name)
        """
        key = node_key(x, y)

        if key not in self.nodes:
            if name is not False:  # Check 'is not False' to allow name=0
                self.nodes[key] = name
            else:
                # Find next available number
                existing_numbers = [v for v in self.nodes.values() if isinstance(v, int)]
                next_num = max(existing_numbers, default=0) + 1
                self.nodes[key] = next_num

        return self.nodes[key]

    def sort_nodes(self):
        """
        Sort nodes dictionary to have consistent ordering.
        Sorts by value (int nodes first, then string nodes).
        """
        sorted_items = sorted(self.nodes.items(), key=lambda item: (isinstance(item[1], str), item[1]))
        self.nodes = dict(sorted_items)

    def make_nodes_from_wires(self, parsed_data):
        """Extract nodes from wire definitions.

        - Creates a node for each unique wire endpoint coordinate.
        - Treats ground flags specially:
            * If there is only one physical ground location, all grounds are node 0.
            * If there are multiple distinct ground locations, they become 0_1, 0_2, ...
        - All non-ground FLAG labels are ignored for node naming; those nodes
          get auto-numbered integer IDs.
        """
        # Reset node map
        self.nodes = {}

        # ---------- 1) Collect all ground FLAG locations ----------
        ground_locations = []

        for line in parsed_data:
            if not line:
                continue

            # Nested FLAGs attached to a WIRE line: scan ALL items after coords
            if line[0] == "WIRE" and len(line) > 5:
                for item in line[5:]:
                    if isinstance(item, list) and item and item[0] == "FLAG":
                        x, y, name = item[1:4]
                        if name == "0" or name == 0:
                            ground_locations.append((x, y))

            # Standalone FLAG line (not attached to symbol or wire)
            if isinstance(line[0], list) and line[0][0] == "FLAG":
                x, y, name = line[0][1:4]
                if name == "0" or name == 0:
                    ground_locations.append((x, y))

        # Decide if all grounds are at the same location
        unique_grounds = list(set(ground_locations))
        single_ground = len(unique_grounds) <= 1

        # Map from (x, y) → "0_1", "0_2", ...
        ground_map = {}
        ground_counter = 1

        # ---------- 2) Process all FLAGs to create nodes ----------
        for line in parsed_data:
            if not line:
                continue

            # Nested FLAGs on WIRE lines – scan ALL items after coords
            if line[0] == "WIRE" and len(line) > 5:
                for item in line[5:]:
                    if isinstance(item, list) and item and item[0] == "FLAG":
                        x, y, name = item[1:4]

                        if name == "0" or name == 0:
                            # Ground node
                            if single_ground:
                                # All grounds share a single node 0
                                self.add_node(x, y, name=0)
                            else:
                                # Multiple independent grounds
                                loc = (x, y)
                                if loc not in ground_map:
                                    ground_map[loc] = f"0_{ground_counter}"
                                    ground_counter += 1
                                self.add_node(x, y, name=ground_map[loc])
                        else:
                            # Non-ground label: ensure node exists, but do not use text as node name
                            self.add_node(x, y)

            # Standalone FLAG (not attached to SYMBOL/WIRE group)
            if isinstance(line[0], list) and line[0][0] == "FLAG":
                x, y, name = line[0][1:4]

                if name == "0" or name == 0:
                    if single_ground:
                        self.add_node(x, y, name=0)
                    else:
                        loc = (x, y)
                        if loc not in ground_map:
                            ground_map[loc] = f"0_{ground_counter}"
                            ground_counter += 1
                        self.add_node(x, y, name=ground_map[loc])
                else:
                    # Non-ground label: ensure node exists, but do not use text as node name
                    self.add_node(x, y)

        # ---------- 3) Add nodes for all wire endpoints ----------
        for line in parsed_data:
            if not line or line[0] != "WIRE":
                continue

            # Wire format: WIRE x1 y1 x2 y2 ...
            x1, y1, x2, y2 = line[1:5]

            # Add nodes at endpoints (reuses any existing ground node or numbered node)
            self.add_node(x1, y1)
            self.add_node(x2, y2)

    def extract_nets(self, parsed_data):
        """Extract electrical nets using NetworkX graph analysis.

        Builds a graph where nodes are wire endpoints and edges are wires,
        then finds connected components to identify nets.

        Args:
            parsed_data: Parsed LTspice data

        Returns:
            dict: Mapping from coordinate keys to net identifiers
        """
        wire_graph = nx.Graph()

        # Add edges for all wires
        for line in parsed_data:
            if not line or line[0] != "WIRE":
                continue

            x1, y1, x2, y2 = line[1:5]
            key1 = node_key(x1, y1)
            key2 = node_key(x2, y2)

            wire_graph.add_edge(key1, key2)

        # Find connected components (nets)
        nets = list(nx.connected_components(wire_graph))

        # Create mapping from node key to net identifier
        net_map = {}

        # Start numbering from 1 (0 reserved for ground-style nodes)
        net_num = 1

        def _is_ground_value(value):
            """Return True if a node value represents a ground node.

            Treats 0, "0", and names like "0_1", "0_2", ... as ground.
            """
            if value == 0:
                return True
            if isinstance(value, str):
                if value == "0" or value.startswith("0_"):
                    return True
            return False

        for net in nets:
            # Collect any ground-style node values that appear in this net
            ground_values = []
            for key in net:
                if key in self.nodes and _is_ground_value(self.nodes[key]):
                    ground_values.append(self.nodes[key])

            if ground_values:
                # Use the first ground-style value (0, "0_1", "0_2", ...) as
                # the identifier for this entire connected net.
                base_value = ground_values[0]
                for key in net:
                    net_map[key] = base_value
            else:
                # Assign a regular numbered net
                for key in net:
                    net_map[key] = net_num
                net_num += 1

        return net_map

    def make_nodes_with_net_extraction(self, parsed_data):
        """
        Create nodes dictionary using net extraction.

        Uses NetworkX to identify electrically connected nets and assigns
        the same node number to all points in the same net.

        Args:
            parsed_data: Parsed LTspice data
        """
        # First, create all nodes using standard method
        self.make_nodes_from_wires(parsed_data)

        # Extract nets
        net_map = self.extract_nets(parsed_data)

        # Update nodes dictionary with net numbers
        for key in self.nodes.keys():
            if key in net_map:
                self.nodes[key] = net_map[key]

    def rebuild_from_netlist(self, netlist):
        """
        Rebuild nodes dictionary from a netlist string.

        This is needed after transformations like renumbering to sync
        the nodes dict with the netlist.

        Args:
            netlist: Netlist string
        """
        self.nodes = {}

        for line in netlist.split("\n"):
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            comp = parts[0]

            # Extract nodes based on component type
            if comp.startswith("E") and len(parts) >= 6:
                # Op-amp: positions 1, 2, 4, 5
                nodes_in_line = [
                    parts[1].rstrip(";"),
                    parts[2].rstrip(";"),
                    parts[4].rstrip(";"),
                    parts[5].rstrip(";"),
                ]
            elif comp.startswith("W") or len(parts) >= 3:
                # Wire or two-terminal: positions 1, 2
                nodes_in_line = [parts[1].rstrip(";"), parts[2].rstrip(";")]
            else:
                continue

            # Add nodes to dictionary
            for node in nodes_in_line:
                if node not in self.nodes:
                    # Try to parse as integer, otherwise keep as string
                    try:
                        # Handle ground nodes like 0_1, 0_2
                        if node.startswith("0_"):
                            self.nodes[node] = node  # Keep as string
                        else:
                            self.nodes[node] = int(node)
                    except ValueError:
                        self.nodes[node] = node  # Keep as string if not a number
