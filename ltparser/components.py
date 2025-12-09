"""
Component handling for ltparser.

Handles component-specific logic, pin matching, and coordinate transformations.
"""

from .config import COMPONENTS_CONFIG


def node_key(x, y):
    """Create a unique key for a node at coordinates (x, y)."""
    return f"{x:04d}_{y:04d}"


def rotate_point(x, y, direction):
    """
    Rotate a point based on component direction.

    Args:
        x: horizontal coordinate of point
        y: vertical coordinate of point
        direction: 'down' (R0), 'left' (R90), 'up' (R180), 'right' (R270)

    Returns:
        tuple: Rotated (x, y) coordinates
    """
    rotations = {
        "down": (x, y),  # R0
        "left": (-y, x),  # R90
        "up": (-x, -y),  # R180
        "right": (y, -x),  # R270
    }
    return rotations.get(direction, (x, y))


class ComponentMatcher:
    """Handles matching component pins to circuit nodes."""

    def __init__(self, nodes_dict):
        """
        Initialize component matcher.

        Args:
            nodes_dict: Dictionary mapping node keys to node numbers
        """
        self.nodes = nodes_dict

    def match_opamp_nodes(self, x, y, direction):
        """
        Match 5-pin op-amp (UniversalOpamp2) pins to circuit nodes.

        Args:
            x: horizontal coordinate of op-amp origin
            y: vertical coordinate of op-amp origin
            direction: Orientation ('down', 'left', 'up', 'right')

        Returns:
            Dict mapping pin names to node numbers/names
        """
        # Pin positions in default orientation (down/R0)
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
        """
        Match simple 3-pin op-amp to circuit nodes.

        The simple opamp symbol has only 3 pins: in+, in-, and out.
        No explicit power pins.

        Args:
            x: horizontal coordinate of op-amp origin
            y: vertical coordinate of op-amp origin
            direction: Orientation ('down', 'left', 'up', 'right')

        Returns:
            Dict mapping pin names to node numbers/names
        """
        # Pin positions for simple 3-pin op-amp in default orientation (down/R0)
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

    def match_node(self, x, y, kind, direction):
        """
        Match a component at position (x, y) to its connected nodes.

        Args:
            x: horizontal coordinate of component
            y: vertical coordinate of component
            x, y: Component coordinates
            kind: Component type/symbol
            direction: Component orientation

        Returns:
            dict: Node mapping for this component
        """
        # Handle op-amps specially
        if kind in ("Opamps/UniversalOpamp2", "opamp"):
            if kind == "Opamps/UniversalOpamp2":
                return self.match_opamp_nodes(x, y, direction)
            else:
                return self.match_simple_opamp_nodes(x, y, direction)

        # Look for component in config
        # Check two_terminal components
        components_config = COMPONENTS_CONFIG.get("components", {})
        two_term = components_config.get("two_terminal", {})
#        multi_term = components_config.get("multi_terminal", {})
#        three_term = components_config.get("three_terminal", {})

        config = None
        if kind in two_term:
            config = two_term[kind]
        elif kind.lower().startswith("res") and "res" in two_term:
            config = two_term["res"]
        elif kind.lower().startswith("cap") and "cap" in two_term:
            config = two_term["cap"]
        elif kind.lower().startswith("ind") and "ind" in two_term:
            config = two_term["ind"]
        elif kind.lower() == "voltage" or kind.lower().startswith("voltage"):
            config = two_term.get("voltage")
        elif kind.lower() == "current" or kind.lower().startswith("current"):
            config = two_term.get("current")
        elif kind.lower() == "ammeter" or kind.lower().startswith("ammeter"):
            config = two_term.get("ammeter")
        elif kind.lower() == "voltmeter" or kind.lower().startswith("voltmeter"):
            config = two_term.get("voltmeter")

        if config and "x_offset" in config:
            # Two-terminal component with offsets
            x_off = config["x_offset"]
            y_off = config["y_offset"]
            length = config["length"]

            # Calculate pin positions
            # Pin 1 at (x + x_off, y + y_off)
            # Pin 2 at (x + x_off, y + length) for down orientation
            if direction == "down" or direction == "R0" or direction == "R":
                pin1_x, pin1_y = x + x_off, y + y_off
                pin2_x, pin2_y = x + x_off, y + length
            elif direction == "right" or direction == "R270":
                # Rotate 90° CW: (x,y) -> (y, -x)
                pin1_x, pin1_y = x + y_off, y - x_off
                pin2_x, pin2_y = x + length, y - x_off
            elif direction == "up" or direction == "R180":
                # Rotate 180°: (x,y) -> (-x, -y)
                pin1_x, pin1_y = x - x_off, y - y_off
                pin2_x, pin2_y = x - x_off, y - length
            elif direction == "left" or direction == "R90":
                # Rotate 90° CCW: (x,y) -> (-y, x)
                pin1_x, pin1_y = x - y_off, y + x_off
                pin2_x, pin2_y = x - length, y + x_off
            else:
                # Default to down
                pin1_x, pin1_y = x + x_off, y + y_off
                pin2_x, pin2_y = x + x_off, y + length

            key1 = node_key(pin1_x, pin1_y)
            key2 = node_key(pin2_x, pin2_y)

            return {
                "n1": self.nodes.get(key1, "?"),
                "n2": self.nodes.get(key2, "?"),
                "pin0": self.nodes.get(key1, "?"),
                "pin1": self.nodes.get(key2, "?"),
            }

        # Default: assume two-terminal at origin and direction-dependent endpoint
        direction_offsets = {"right": (16, 0), "down": (0, 16), "left": (-16, 0), "up": (0, -16)}

        offset = direction_offsets.get(direction, (16, 0))
        key1 = node_key(x, y)
        key2 = node_key(x + offset[0], y + offset[1])

        return {"n1": self.nodes.get(key1, "?"), "n2": self.nodes.get(key2, "?")}
