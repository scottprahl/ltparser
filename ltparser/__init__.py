"""
ltparser - LTspice circuit file parser

A Python library for parsing LTspice .asc files and generating netlists
compatible with lcapy for symbolic circuit analysis.
"""

from .parser import LTspice
from .nodes import NodeManager
from .netlist import NetlistGenerator
from .components import ComponentMatcher
from .transformations import NetlistTransformer

__version__ = "0.2.0"
__author__ = "Scott"

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
