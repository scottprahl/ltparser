"""
ltparser - LTspice circuit file parser.

A Python library for parsing LTspice .asc files and generating netlists
compatible with lcapy for symbolic circuit analysis.
"""

from .parser import LTspice
from .nodes import NodeManager
from .netlist import NetlistGenerator
from .components import ComponentMatcher
from .transformations import NetlistTransformer

__version__ = "0.3.0"
__author__ = "Scott Prahl"
__email__ = "scott.prahl@oit.edu"
__copyright__ = "2024-25 Scott Prahl"
__license__ = "MIT"
__url__ = "https://github.com/scottprahl/ltparser.git"


__all__ = [
    "LTspice",
    "NodeManager",
    "NetlistGenerator",
    "ComponentMatcher",
    "NetlistTransformer",
    # Expose transformation functions directly
    "renumber_grounds",
    "renumber_nodes",
]

# Convenience exports
renumber_grounds = NetlistTransformer.renumber_grounds
renumber_nodes = NetlistTransformer.renumber_nodes
