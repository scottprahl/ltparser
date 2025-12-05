"""
Convert the contents of an LTspice .asc file to a netlist for use in lcapy.

Example:
    First, import the required module:

    .. code-block:: python

        import ltparser

    Then use the module to load, process, and visualize an LTspice schematic:

    .. code-block:: python

        >>> lt = ltparser.LTspice()
        >>> lt.read('circuit.asc')
        >>> lt.make_netlist()
        >>> cct = lt.circuit()
        >>> cct.draw()

This sequence initializes the LTspice parser, reads a schematic, creates a netlist,
and finally visualizes the circuit using lcapy.
"""

import matplotlib.pyplot as plt
import pyparsing as pp
import lcapy
import networkx as nx

__all__ = (
    "ltspice_value_to_number",
    "rotate_point",
    "node_key",
    "LTspice",
)


# Specific exception
class LTspiceFileError(ValueError):
    """Raised when file is not a valid LTspice file."""


component_offsets = {
    # each entry has x_off, y_off, and length
    "voltage": [0, 16, 96],
    "cap": [16, 0, 64],
    "res": [16, 16, 96],
    "current": [0, 0, 80],
    "polcap": [16, 0, 64],
    "ind": [16, 16, 96],
    "Opamps/UniversalOpamp2": [[-32, -16], [-32, 16], [32, -0], [0, -32], [0, 32]],
}


def node_key(x, y):
    """Cast LTspice x,y location to a key for a dictionary."""
    return "%04d_%04d" % (int(x), int(y))


def the_direction(line):
    """Determine the direction of the two nodes."""
    x1 = int(line[1])
    y1 = int(line[2])
    x2 = int(line[3])
    y2 = int(line[4])

    if x1 == x2:
        if y1 > y2:
            return "up"
        return "down"

    if x1 > x2:
        return "left"

    return "right"


def rotate_point(x, y, direction):
    """Rotate a point based on component direction.

    Args:
        x: X coordinate relative to component origin
        y: Y coordinate relative to component origin
        direction: One of 'down', 'left', 'up', 'right'

    Returns:
        Tuple of (rotated_x, rotated_y)
    """
    rotations = {
        "down": lambda px, py: (px, py),  # 0 degrees
        "left": lambda px, py: (py, -px),  # 90 degrees CCW
        "up": lambda px, py: (-px, -py),  # 180 degrees
        "right": lambda px, py: (-py, px),  # 270 degrees CCW
    }
    return rotations[direction](x, y)


def ltspice_sine_parser(s):
    """Try and figure out offset, amplitude, and frequency."""
    number = pp.Combine(
        pp.Optional(".") + pp.Word(pp.nums) + pp.Optional("." + pp.Optional(pp.Word(pp.nums)))
    )
    sine = pp.Literal("SINE(") + pp.Optional(number) * 3 + pp.Literal(")")

    parsed = sine.parseString(s)
    dc = 0
    amp = 1
    omega = 0
    if parsed[1] == ")":
        return dc, amp, omega

    dc = float(parsed[1])

    if parsed[2] == ")":
        return dc, amp, omega

    amp = float(parsed[2])
    if parsed[3] == ")":
        return dc, amp, omega

    omega = float(parsed[3])

    return dc, amp, omega


def ltspice_value_to_number(s):
    """Convert LTspice value 4.7k to 4700."""
    #    print("converting ", s)
    # sometimes "" shows up as the value
    empty = pp.Literal('""')
    try:
        empty.parseString(s)
        return ""
    except pp.ParseException:
        pass

    # return things like {R} untouched
    parameter = pp.Combine("{" + pp.restOfLine())
    try:
        parameter.parseString(s)
        return s
    except pp.ParseException:
        pass

    # this does not handle 1e-3
    # this does not handle 1e-3
    number = pp.Combine(
        pp.Optional(".") + pp.Word(pp.nums) + pp.Optional("." + pp.Optional(pp.Word(pp.nums)))
    )

    # the SI prefixes
    prefix = (
        pp.CaselessLiteral("MEG")
        | pp.CaselessLiteral("F")
        | pp.CaselessLiteral("P")
        | pp.CaselessLiteral("N")
        | pp.CaselessLiteral("U")
        | pp.CaselessLiteral("M")
        | pp.CaselessLiteral("K")
        | pp.Literal("µ")
    )

    # use restOfLine to discard possible unwanted units
    lt_number = number + pp.Optional(prefix) + pp.restOfLine()

    try:
        parsed = lt_number.parseString(s)
        x = float(parsed[0])

        # change number based on unit prefix
        if parsed[1] == "F":
            x *= 1e-15
        elif parsed[1] == "P":
            x *= 1e-12
        elif parsed[1] == "N":
            x *= 1e-9
        elif parsed[1] == "U" or parsed[1] == "µ":
            x *= 1e-6
        elif parsed[1] == "M":
            x *= 1e-3
        elif parsed[1] == "K":
            x *= 1e3
        elif parsed[1] == "MEG":
            x *= 1e6
        return x
    except pp.ParseException:
        pass

    return s


class LTspice:
    """Class to convert LTspice files to lcapy circuits."""

    def __init__(self):
        """Initialize object variables."""
        self.contents = None
        self.parsed = None
        self.nodes = None
        self.netlist = None
        self.single_ground = True
        self.graph = None

    def read(self, filename):
        """Read a file as contents."""
        encodings = []
        with open(filename, "rb") as f:
            byte1 = f.read(1)
            byte2 = f.read(1)

        if byte1 != b"V":
            raise LTspiceFileError("This is not an LTspice file.")

        if byte2 == b"e":
            encodings = ["utf-8", "mac-roman", "windows-1250"]
        elif byte2 == b"\x00":
            encodings = ["utf-16-le"]
        else:
            raise LTspiceFileError("This is not an LTspice file.")

        for e in encodings:
            try:
                with open(filename, "r", encoding=e) as f:
                    x = f.read()
                    self.contents = x.replace("µ", "u")
                    break
            except UnicodeError:
                print("got unicode error with %s , trying different encoding" % e)
            else:
                print("opening the file with encoding:  %s " % e)
                break

    def parse(self):
        """Parse LTspice .asc file contents."""
        heading = pp.Group(pp.Keyword("Version") + pp.Literal("4"))
        integer = pp.Combine(pp.Optional(pp.Char("-")) + pp.Word(pp.nums))
        label = pp.Word(pp.alphanums + "_" + "µ" + "-" + "+" + "/")
        sheet = pp.Group(pp.Keyword("SHEET") + integer * 3)
        rotation = pp.Group(pp.Char("R") + integer)
        wire = pp.Group(pp.Keyword("WIRE") + integer * 4)
        window = pp.Group(pp.Keyword("WINDOW") + pp.restOfLine())
        symbol = pp.Group(pp.Keyword("SYMBOL") + label + integer * 2 + rotation)
        attr = pp.Group(pp.Keyword("SYMATTR") + label + pp.White() + pp.restOfLine())
        flag = pp.Group(pp.Keyword("FLAG") + integer * 2 + label)
        iopin = pp.Group(pp.Keyword("IOPIN") + integer * 2 + label)
        text = pp.Group(pp.Keyword("TEXT") + pp.restOfLine())
        line = pp.Group(pp.Keyword("LINE") + pp.restOfLine())
        rect = pp.Group(pp.Keyword("RECTANGLE") + pp.restOfLine())

        component = pp.Group(symbol + pp.Dict(pp.ZeroOrMore(window)) + pp.Dict(pp.ZeroOrMore(attr)))
        linetypes = wire | flag | iopin | component | line | text | rect

        grammar = heading + sheet + pp.Dict(pp.ZeroOrMore(linetypes))
        if self.contents is not None:
            self.parsed = grammar.parseString(self.contents)

    def print_parsed(self):
        """Better visualization of parsed LTspice file."""
        if self.parsed is None:
            print("Nothing parsed yet.")

        for line in self.parsed:
            element = line[0]

            if isinstance(element, pp.ParseResults):
                print(line[0])
                for i in range(1, len(line)):
                    print("    ", line[i])
                continue
            print(element, line[1:])

    def sort_nodes(self):
        """Sorts the notes a dict with nodes sorted."""
        return

    #         sorted_keys = sorted(self.nodes)
    #
    #         grounds = 0
    #         for key in sorted_keys:
    #             if self.nodes[key] == 0:
    #                 grounds += 1
    #
    #         count = 1
    #         for key in sorted_keys:
    #             if self.nodes[key] != 0:
    #                 self.nodes[key] = count
    #                 count += 1

    def print_nodes(self):
        """Print the notes a dict with nodes sorted."""
        for key in self.nodes:
            print(key, " : ", self.nodes[key])

    def plot_nodes(self):
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

    def add_node(self, x, y, name=False):
        """Add a new node."""
        n = node_key(x, y)
        if n in self.nodes:
            return

        if name:
            name = name.replace("_", "•", 1)
            name = name.replace("_", "")
            name = name.replace("•", "_")
            self.nodes[n] = name
            return

        self.nodes[n] = len(self.nodes) + 1

    def make_nodes_from_wires(self):
        """
        Produce the dictionary of nodes for all wires and grounds.

        The grounds need to be processed first so that they can all get
        labelled with "0".  Then the end of each wire is examined.  If
        the x,y location has been seen before, it is ignored.  If it has
        not, then it is added to the dictionary of nodes.
        """
        self.nodes = {}
        if self.parsed is None:
            return

        # create ground nodes and other labelled nodes
        ground_count = 0
        for line in self.parsed:
            if line[0] == "FLAG":
                self.add_node(line[1], line[2], line[3])
                if line[3] == 0 or line[3] == "0":
                    ground_count += 1

        self.single_ground = ground_count <= 1

        # now wire nodes
        for line in self.parsed:
            if line[0] == "WIRE":
                self.add_node(line[1], line[2])
                self.add_node(line[3], line[4])

    def make_nodes_with_net_extraction(self):
        """
        Produce node dictionary using net extraction from wire connectivity.

        This method uses graph analysis to identify electrical nets, then assigns
        the same node number to all points in the same net. This is essential for
        generating netlists without explicit wires.
        """
        self.nodes = {}
        if self.parsed is None:
            return

        # First, extract nets from wire connectivity
        net_mapping = self.extract_nets()

        # Assign nodes based on net extraction
        for node_key, net_num in net_mapping.items():
            self.nodes[node_key] = net_num

        # Update ground count
        ground_count = sum(1 for v in self.nodes.values() if v == 0)
        self.single_ground = ground_count <= 1

    def match_opamp_nodes(self, x, y, direction):
        """Match op-amp pins to circuit nodes.

        Args:
            x: X coordinate of op-amp origin
            y: Y coordinate of op-amp origin
            direction: Orientation ('down', 'left', 'up', 'right')

        Returns:
            Dict mapping pin names to node numbers/names
        """
        # Pin positions in default orientation (down/R0)
        # These match the offsets in component_offsets for Opamps/UniversalOpamp2
        pin_positions = {
            "in_minus": (-32, -16),  # Inverting input
            "in_plus": (-32, 16),  # Non-inverting input
            "out": (32, 0),  # Output
            "vcc": (0, -32),  # V+ power
            "vee": (0, 32),  # V- power
        }

        nodes = {}
        for pin_name, (px, py) in pin_positions.items():
            # Rotate pin position based on component direction
            rx, ry = rotate_point(px, py, direction)

            # Get node at this location
            key = node_key(x + rx, y + ry)
            nodes[pin_name] = self.nodes.get(key, "?")

        return nodes

    def match_simple_opamp_nodes(self, x, y, direction):
        """Match simple 3-pin op-amp to circuit nodes.

        The simple opamp symbol has only 3 pins: in+, in-, and out.
        No explicit power pins.

        Args:
            x: X coordinate of op-amp origin
            y: Y coordinate of op-amp origin
            direction: Orientation ('down', 'left', 'up', 'right')

        Returns:
            Dict mapping pin names to node numbers/names
        """
        # Pin positions for simple 3-pin op-amp in default orientation (down/R0)
        # Based on actual LTspice opamp symbol measurements
        pin_positions = {
            "in_plus": (-32, 48),  # Non-inverting input (top left)
            "in_minus": (-32, 80),  # Inverting input (bottom left)
            "out": (32, 64),  # Output (right)
        }

        nodes = {}
        for pin_name, (px, py) in pin_positions.items():
            # Rotate pin position based on component direction
            rx, ry = rotate_point(px, py, direction)

            # Get node at this location
            key = node_key(x + rx, y + ry)
            nodes[pin_name] = self.nodes.get(key, "?")

        return nodes

    def extract_nets(self):
        """Extract electrical nets from wire connectivity using graph analysis.

        This assigns the same node number to all electrically connected points,
        which is essential for generating a correct netlist without explicit wires.

        Returns:
            dict: Mapping from node position keys to net numbers
        """
        import networkx as nx

        # Build connectivity graph from wires
        wire_graph = nx.Graph()

        # Add all wire connections
        for line in self.parsed:
            if line[0] == "WIRE":
                # Get wire endpoints
                x1, y1 = int(line[1]), int(line[2])
                x2, y2 = int(line[3]), int(line[4])

                # Create node keys
                n1_key = node_key(x1, y1)
                n2_key = node_key(x2, y2)

                # Add edge connecting the endpoints
                wire_graph.add_edge(n1_key, n2_key)

        # Find connected components (each is one electrical net)
        nets = list(nx.connected_components(wire_graph))

        # Assign net numbers
        net_mapping = {}
        next_net_num = 1

        for net_nodes in nets:
            # Reserve net 0 for ground
            # Check if any node in this net is already marked as ground
            is_ground_net = False
            for nkey in net_nodes:
                # If nodes dict already exists and has ground marked
                if self.nodes and self.nodes.get(nkey) in (0, "0", "GND", "gnd"):
                    is_ground_net = True
                    break
                # Check for ground flag names
                for flag_line in self.parsed:
                    if flag_line[0] == "FLAG":
                        fx, fy = int(flag_line[1]), int(flag_line[2])
                        flag_key = node_key(fx, fy)
                        if flag_key == nkey and flag_line[3] in ("0", "GND", "gnd"):
                            is_ground_net = True
                            break
                if is_ground_net:
                    break

            # Assign net number
            if is_ground_net:
                net_num = 0
            else:
                net_num = next_net_num
                next_net_num += 1

            # Map all nodes in this net to the same number
            for nkey in net_nodes:
                net_mapping[nkey] = net_num

        return net_mapping

    def wire_to_netlist(self, line):
        """Return netlist string for one wire in parsed data."""
        if line[0] != "WIRE":
            return

        n1 = self.nodes[node_key(line[1], line[2])]
        n2 = self.nodes[node_key(line[3], line[4])]

        direction = the_direction(line)

        # make the wires all go right or down
        if direction == "up":
            n1, n2 = n2, n1
            direction = "down"
        if direction == "left":
            n1, n2 = n2, n1
            direction = "right"

        self.graph.add_edge(n1, n2)

        # Include direction hints based on mode
        # In non-minimal mode, always include directions (helpful for debugging)
        # In minimal mode, never include directions (let lcapy auto-layout)
        in_minimal_mode = getattr(self, "_minimal", False)
        include_directions = getattr(self, "_include_wire_directions", False)

        if not in_minimal_mode and not include_directions:
            # Default: include directions in non-minimal mode
            self.netlist += "W %s %s; %s\n" % (n1, n2, direction)
        elif include_directions:
            # Explicitly requested directions
            self.netlist += "W %s %s; %s\n" % (n1, n2, direction)
        else:
            # Minimal mode or explicitly no directions
            self.netlist += "W %s %s\n" % (n1, n2)

    def symbol_to_netlist(self, line):
        """Return netlist string for symbol in parsed data."""
        first = list(line[0])
        if first[0] != "SYMBOL":
            return

        kind = first[1]
        #        print("\nKind==", kind)

        x = int(first[2])
        y = int(first[3])

        rotation = list(first[4])[1]
        if rotation == "0":
            direction = "down"
        elif rotation == "90":
            direction = "left"
        elif rotation == "180":
            direction = "up"
        else:
            direction = "right"

        name = ""
        value = ""
        _value2 = None

        # Handle op-amp components early (both types)
        if kind in ("Opamps/UniversalOpamp2", "opamp"):
            # Get the component name first
            for sub_line in line:
                row = list(sub_line)
                if row[0] == "SYMATTR" and row[1] == "InstName":
                    name = row[3]
                    break

            # Lcapy requires op-amps to use 'E' prefix, not 'U'
            # Convert U1 -> E1, U2 -> E2, etc.
            if name.startswith("U"):
                name = "E" + name[1:]

            # Match op-amp pins to nodes (different methods for different types)
            if kind == "Opamps/UniversalOpamp2":
                # 5-pin op-amp with explicit power pins
                nodes = self.match_opamp_nodes(x, y, direction)
                ref_node = nodes["vee"] if nodes["vee"] != 0 else 0
            else:
                # Simple 3-pin op-amp (kind == "opamp")
                nodes = self.match_simple_opamp_nodes(x, y, direction)
                ref_node = 0  # Reference to ground for simple op-amp

            # Generate netlist line in lcapy format
            # Lcapy format: Ename Nout Nref opamp Ninp Ninm [Ad] [Ac]
            # where Nref is the reference node (usually ground or vee)
            self.netlist += f"{name} {nodes['out']} {ref_node} opamp "
            self.netlist += f"{nodes['in_plus']} {nodes['in_minus']}\n"

            # Add nodes to graph
            for node in nodes.values():
                if node != "?":
                    self.graph.add_node(node)

            # Add edges connecting all op-amp pins
            node_list = [n for n in nodes.values() if n != "?"]
            for i, n1 in enumerate(node_list):
                for n2 in node_list[i + 1 :]:
                    self.graph.add_edge(n1, n2)

            return  # Done with this op-amp, don't continue to two-terminal logic

        for sub_line in line:
            row = list(sub_line)

            if row[0] != "SYMATTR":
                continue

            if row[1] == "InstName":
                name = row[3]
                name = name.replace("_", "•", 1)
                name = name.replace("_", "")
                name = name.replace("•", "_")
                continue

            if row[1] == "Value":
                value = row[3]
                continue

            if row[1] == "Value2":
                _value2 = row[3]
                continue

        node1, node2 = self.match_node(x, y, kind, direction)

        if value != "":
            value = ltspice_value_to_number(value)

        if kind == "current":
            direction += ", invert"

        if kind in ("current", "voltage"):
            if not isinstance(value, float):
                try:
                    _dc, amp, _omega0 = ltspice_sine_parser(value)
                    self.graph.add_edge(node1, node2)
                    self.netlist += "%s %s %s ac %f; %s\n" % (name, node1, node2, amp, direction)
                    return
                except pp.ParseException:
                    pass

        if kind == "polcap":
            direction += ", kind=polar, invert"

        # Check if we need to reorient this RLC component
        should_swap_nodes = False
        if getattr(self, "_do_reorient_rlc", False):
            # Check if this is an R, L, or C component
            is_rlc = name.startswith("R") or name.startswith("L") or name.startswith("C")
            if is_rlc:
                # Check if direction is left or up (needs reorienting)
                if direction in ("left", "up"):
                    should_swap_nodes = True
                    # Update direction for non-minimal mode
                    if direction == "left":
                        direction = "right"
                    elif direction == "up":
                        direction = "down"

        # Swap nodes if needed
        if should_swap_nodes:
            node1, node2 = node2, node1

        self.graph.add_edge(node1, node2)

        # In minimal mode, omit all direction hints
        if getattr(self, "_minimal", False):
            self.netlist += "%s %s %s %s\n" % (name, node1, node2, value)
        else:
            self.netlist += "%s %s %s %s; %s\n" % (name, node1, node2, value, direction)

    def _reorient_rlc(self):
        """
        Reorient resistors, capacitors, and inductors to only go right or down.

        This helps lcapy's layout algorithm by ensuring all passive components
        have consistent orientation. Components going left become right (with swapped nodes),
        and components going up become down (with swapped nodes).

        Modifies self.netlist in place.
        """
        if not self.netlist:
            return

        # Parse the netlist into lines
        lines = self.netlist.strip().split("\n")
        reoriented_lines = []

        for line in lines:
            if not line.strip():
                continue

            # Check if this is an R, L, or C component
            parts = line.split()
            if len(parts) < 3:
                reoriented_lines.append(line)
                continue

            component_name = parts[0]
            is_rlc = (
                component_name.startswith("W")
                or component_name.startswith("R")
                or component_name.startswith("L")
                or component_name.startswith("C")
            )

            if not is_rlc:
                reoriented_lines.append(line)
                continue

            # Parse the line: "R1 node1 node2 value; direction"
            if ";" in line:
                main_part, direction_part = line.split(";", 1)
                direction = direction_part.strip()
            else:
                # No direction specified
                reoriented_lines.append(line)
                continue

            main_parts = main_part.split()
            if len(main_parts) < 4:
                reoriented_lines.append(line)
                continue

            name = main_parts[0]
            node1 = main_parts[1]
            node2 = main_parts[2]
            value = main_parts[3]

            # Check if direction needs reorienting
            needs_reorient = False
            new_direction = direction

            if "left" in direction.lower():
                needs_reorient = True
                new_direction = direction.lower().replace("left", "right")
            elif "up" in direction.lower():
                needs_reorient = True
                new_direction = direction.lower().replace("up", "down")

            if needs_reorient:
                # Swap nodes
                node1, node2 = node2, node1
                reoriented_line = f"{name} {node1} {node2} {value}; {new_direction}"
                reoriented_lines.append(reoriented_line)
            else:
                reoriented_lines.append(line)

        # Reconstruct netlist
        self.netlist = "\n".join(reoriented_lines) + "\n"

    def _renumber_nodes_for_drawing(self):
        """
        Renumber nodes sequentially with 'x' marker system.

        Algorithm:
        1. Pass 1: Mark EACH ground occurrence as 0_1x, 0_2x, 0_3x, etc.
        2. Pass 2: Mark non-ground nodes as 1x, 2x, 3x in order of appearance
        3. Pass 3: If only one ground (one 0_x), change it to 0x
        4. Pass 4: Remove all 'x' markers
        """
        if not self.netlist:
            return

        result = self.netlist

        # PASS 1: Mark EACH ground occurrence uniquely
        ground_counter = 0
        lines = result.split("\n")
        new_lines = []

        for line in lines:
            if not line.strip():
                new_lines.append(line)
                continue

            parts = line.split()
            if len(parts) < 3:
                new_lines.append(line)
                continue

            # Check each node position and replace ground (0)
            new_line = line
            comp = parts[0]

            if comp.startswith("E") and len(parts) >= 6:
                # Op-amp: check positions 1, 2, 4, 5
                positions = [1, 2, 4, 5]
            else:
                # Two-terminal: check positions 1, 2
                positions = [1, 2]

            # Replace each occurrence of ' 0' in the appropriate positions
            # We need to be careful to replace the right instances
            parts_modified = parts[:]
            for pos in positions:
                if pos < len(parts) and parts[pos].rstrip(";") == "0":
                    ground_counter += 1
                    if parts[pos].endswith(";"):
                        parts_modified[pos] = f"0_{ground_counter}x;"
                    else:
                        parts_modified[pos] = f"0_{ground_counter}x"

            # Reconstruct the line
            if parts_modified != parts:
                new_line = " ".join(parts_modified)

            new_lines.append(new_line)

        result = "\n".join(new_lines)

        # PASS 2: Mark non-ground nodes in order of first appearance
        next_node_num = 1

        # Keep processing until no more unmarked nodes found
        while True:
            lines = result.split("\n")
            found_unmarked = False

            for line in lines:
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) < 3:
                    continue

                comp = parts[0]

                # Get node positions
                if comp.startswith("E") and len(parts) >= 6:
                    node_positions = [1, 2, 4, 5]
                else:
                    node_positions = [1, 2]

                # Process each node in this line
                for pos in node_positions:
                    if pos >= len(parts):
                        continue

                    node = parts[pos].rstrip(";")

                    # Skip if already marked with 'x' or is ground (0_)
                    if "x" in node or node.startswith("0_"):
                        continue

                    # Found an unmarked node!
                    found_unmarked = True
                    new_node = f"{next_node_num}x"

                    # Replace ALL occurrences in the entire netlist
                    result = result.replace(f" {node};", f" {new_node};")
                    result = result.replace(f" {node} ", f" {new_node} ")
                    result = result.replace(f" {node}\n", f" {new_node}\n")

                    next_node_num += 1
                    break  # Re-parse from the beginning with updated result

                if found_unmarked:
                    break  # Re-parse from the beginning

            if not found_unmarked:
                break  # No more unmarked nodes

        # PASS 3: If only one ground, change 0_1x to 0x
        if ground_counter == 1:
            result = result.replace("0_1x", "0x")

        # PASS 4: Remove all 'x' markers
        result = result.replace("x", "")

        self.netlist = result

    def make_netlist(
        self,
        use_named_nodes=True,
        include_wire_directions=True,
        minimal=False,
        use_net_extraction=False,
        reorient_rlc=True,
        renumber_nodes=True,
    ):
        """Process parsed LTspice data and create a simple netlist.

        Args:
            use_named_nodes: If True, keep named nodes like '+Vs' and '-Vs'.
                           If False (default), convert to numbers for better
                           drawing compatibility with lcapy.
            include_wire_directions: If True, include direction hints (right, down).
                                   If False (default), omit directions to let lcapy
                                   auto-layout, which may work better for complex circuits.
            minimal: If True, only include components (no wires or directions).
                    This gives lcapy complete freedom to auto-layout.
                    Recommended for drawing.
            use_net_extraction: If True, use graph-based net extraction to renumber
                              nodes so electrically connected points have the same number.
                              This is ESSENTIAL for minimal mode to work correctly!
            reorient_rlc: If True, reorient R, L, C components to only go right or down.
                         Helps lcapy's layout by standardizing component orientations.
            renumber_nodes: If True, renumber nodes for better drawing:
                          - Ground nodes get unique IDs: 0_1, 0_2, 0_3, etc.
                          - Other nodes numbered sequentially from 1
                          Helps lcapy position ground connections independently.
        """
        self.netlist = ""
        self.graph = nx.Graph()
        self._include_wire_directions = include_wire_directions  # Store for wire_to_netlist
        self._minimal = minimal  # Store for later use
        self._do_reorient_rlc = reorient_rlc  # Store for symbol_to_netlist (flag)

        if self.parsed is None:
            self.parse()
            if self.parsed is None:
                return

        if self.nodes is None:
            if use_net_extraction:
                # Use net extraction for proper node numbering
                self.make_nodes_with_net_extraction()
            else:
                # Use original method
                self.make_nodes_from_wires()
                self.sort_nodes()

        # Convert named nodes to numbers if requested
        if not use_named_nodes:
            self._convert_named_nodes_to_numbers()

        for line in self.parsed:

            if line[0] == "WIRE":
                # Skip wires in minimal mode
                if not minimal:
                    self.wire_to_netlist(line)

            if isinstance(line[0], pp.ParseResults):
                self.symbol_to_netlist(line)

        # Reorient R, L, C components if requested
        # Note: For minimal mode, we store the reorientation info and apply during symbol_to_netlist
        if reorient_rlc:
            if not minimal:
                # With directions, can reorient after generation
                self._reorient_rlc()
            # For minimal mode, reorientation needs to happen during component generation
            # so we just set a flag (handled in symbol_to_netlist)

        # Renumber nodes for drawing if requested
        if renumber_nodes:
            self._renumber_nodes_for_drawing()
            # Rebuild nodes dictionary from renumbered netlist
            self._rebuild_nodes_from_netlist()

    def _rebuild_nodes_from_netlist(self):
        """Rebuild self.nodes dictionary from the current netlist.

        This is needed after renumbering to sync the nodes dict with the netlist.
        """
        # Clear existing nodes
        self.nodes = {}

        # Extract all unique nodes from netlist
        for line in self.netlist.split("\n"):
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

    def _convert_named_nodes_to_numbers(self):
        """Convert named nodes like '+Vs' and '-Vs' to numbered nodes.

        This helps lcapy's drawing algorithm by avoiding named node clusters.
        """
        # Find the highest numbered node
        max_node = 0
        for value in self.nodes.values():
            if isinstance(value, int) and value != 0:
                max_node = max(max_node, value)

        # Map named nodes to new numbers
        node_mapping = {}
        next_node = max_node + 1

        for key, value in list(self.nodes.items()):
            # Convert non-ground named nodes to numbers
            if isinstance(value, str) and value not in ["0", "?"]:
                if value not in node_mapping:
                    node_mapping[value] = next_node
                    next_node += 1
                self.nodes[key] = node_mapping[value]

    def make_graph(self):
        """Plot the network graph of the circuit."""
        if self.graph is None:
            self.make_netlist()

        nx.draw(self.graph, with_labels=True, font_weight="bold")
        plt.show()

    def match_node(self, x, y, kind, direction):
        """Match ends of simple component to existing nodes."""
        x_off, y_off, length = component_offsets[kind]
        #        print("Original %d %d %s x_off=%d y_off=%d length=%d" %
        #              (x, y, direction, x_off, y_off, length))

        if direction == "left":
            key1 = node_key(x - y_off, y + x_off)
            key2 = node_key(x - length, y + x_off)

        elif direction == "right":
            key1 = node_key(x + y_off, y - x_off)
            key2 = node_key(x + length, y - x_off)

        elif direction == "down":
            key1 = node_key(x + x_off, y + y_off)
            key2 = node_key(x + x_off, y + length)

        elif direction == "up":
            key1 = node_key(x - x_off, y - y_off)
            key2 = node_key(x - x_off, y - length)
        else:
            key1 = None
            key2 = None

        if key1 not in self.nodes:
            n1 = "?"
        else:
            n1 = self.nodes[key1]

        if key2 not in self.nodes:
            n2 = "?"
        else:
            n2 = self.nodes[key2]

        #        print("pt1 %s ==> %s" % (key1,n1))
        #        print("pt2 %s ==> %s" % (key2,n2))

        return n1, n2

    def circuit(self):
        """Create a lcapy circuit."""
        if self.netlist is None:
            self.make_netlist()

        cct = lcapy.Circuit()
        for line in self.netlist.splitlines():
            cct.add(line)

        if not self.single_ground:
            cct.add(";autoground=True")
        return cct
