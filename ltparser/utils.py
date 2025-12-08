"""
Utility functions for ltparser.

Common helper functions used across multiple modules.
"""


def clean_node_name(node_str):
    """
    Clean a node name by removing trailing semicolons.

    Args:
        node_str: Node string, possibly with semicolon

    Returns:
        str: Cleaned node name
    """
    return node_str.rstrip(";")


def parse_direction(line):
    """
    Extract direction from a netlist line if present.

    Args:
        line: Netlist line (e.g., "W 1 2; right")

    Returns:
        tuple: (main_part, direction) or (line, None) if no direction
    """
    if ";" in line:
        main, direction = line.split(";", 1)
        return main, direction.strip()
    return line, None


def format_value(value):
    """
    Format a component value for netlist output.

    Args:
        value: Component value (float, string, or expression)

    Returns:
        str: Formatted value
    """
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def is_ground_node(node):
    """
    Check if a node is a ground node (0 or 0_x).

    Args:
        node: Node identifier (string or int)

    Returns:
        bool: True if ground node
    """
    node_str = str(node)
    return node_str == "0" or node_str.startswith("0_")
