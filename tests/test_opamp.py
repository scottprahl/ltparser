"""
Tests for op-amp functionality in ltparser
"""

from pathlib import Path

from ltparser import LTspice
from ltparser.components import ComponentMatcher, node_key


def test_match_5pin_opamp_down():
    """Test 5-pin op-amp matching in down orientation."""
    # Create nodes at expected 5-pin op-amp pin positions (R0/down orientation)
    nodes = {
        node_key(0, -32): "vcc",  # V+ power (top)
        node_key(-32, -16): "in-",  # Inverting input (left top)
        node_key(-32, 16): "in+",  # Non-inverting input (left bottom)
        node_key(0, 32): "vee",  # V- power (bottom)
        node_key(32, 0): "out",  # Output (right)
    }

    matcher = ComponentMatcher(nodes)
    result = matcher.match_opamp_nodes(0, 0, "down")

    assert result["vcc"] == "vcc"
    assert result["in_minus"] == "in-"
    assert result["in_plus"] == "in+"
    assert result["vee"] == "vee"
    assert result["out"] == "out"


def test_match_5pin_opamp_right():
    """Test 5-pin op-amp matching in right orientation."""
    # Create nodes at expected positions for right/R270 orientation
    # After rotation: (x,y) -> (y, -x)
    nodes = {
        node_key(-32, 0): "vcc",  # Rotated from (0, -32)
        node_key(-16, 32): "in-",  # Rotated from (-32, -16)
        node_key(16, 32): "in+",  # Rotated from (-32, 16)
        node_key(32, 0): "vee",  # Rotated from (0, 32)
        node_key(0, -32): "out",  # Rotated from (32, 0)
    }

    matcher = ComponentMatcher(nodes)
    result = matcher.match_opamp_nodes(0, 0, "right")

    assert result["vcc"] == "vcc"
    assert result["in_minus"] == "in-"
    assert result["in_plus"] == "in+"
    assert result["vee"] == "vee"
    assert result["out"] == "out"


def test_match_3pin_opamp_down():
    """Test 3-pin op-amp matching in down orientation."""
    # Create nodes at expected 3-pin op-amp positions
    nodes = {
        node_key(-32, 48): "in+",  # Non-inverting input (top left)
        node_key(-32, 80): "in-",  # Inverting input (bottom left)
        node_key(32, 64): "out",  # Output (right middle)
    }

    matcher = ComponentMatcher(nodes)
    result = matcher.match_simple_opamp_nodes(0, 0, "down")

    assert result["in_plus"] == "in+"
    assert result["in_minus"] == "in-"
    assert result["out"] == "out"


def test_match_3pin_opamp_left():
    """Test 3-pin op-amp matching in left orientation."""
    # After R90/left rotation: (x,y) -> (-y, x)
    nodes = {
        node_key(-48, -32): "in+",  # Rotated from (-32, 48)
        node_key(-80, -32): "in-",  # Rotated from (-32, 80)
        node_key(-64, 32): "out",  # Rotated from (32, 64)
    }

    matcher = ComponentMatcher(nodes)
    result = matcher.match_simple_opamp_nodes(0, 0, "left")

    assert result["in_plus"] == "in+"
    assert result["in_minus"] == "in-"
    assert result["out"] == "out"


def test_match_opamp_with_numbered_nodes():
    """Test op-amp matching with actual numbered nodes."""
    # Simulated real scenario with numbered nodes
    # Op-amp at origin (368, 240), direction 'down'
    # Pin offsets: in_minus=(-32,-16), in_plus=(-32,16), out=(32,0), vcc=(0,-32), vee=(0,32)
    nodes = {
        node_key(336, 224): 1,  # in_minus at (368-32, 240-16)
        node_key(336, 256): 2,  # in_plus at (368-32, 240+16)
        node_key(400, 240): 3,  # out at (368+32, 240+0)
        node_key(368, 208): 4,  # vcc at (368+0, 240-32)
        node_key(368, 272): 5,  # vee at (368+0, 240+32)
    }

    matcher = ComponentMatcher(nodes)
    result = matcher.match_opamp_nodes(368, 240, "down")

    # Verify we got valid node numbers
    assert result["out"] == 3
    assert result["in_minus"] == 1
    assert result["in_plus"] == 2
    assert result["vcc"] == 4
    assert result["vee"] == 5


def test_opamp_missing_nodes():
    """Test op-amp matching when some nodes are missing."""
    # Only some pins connected
    nodes = {
        node_key(-32, 16): 1,  # in_plus
        node_key(32, 0): 2,  # out
    }

    matcher = ComponentMatcher(nodes)
    result = matcher.match_opamp_nodes(0, 0, "down")

    # Connected pins should have values
    assert result["in_plus"] == 1
    assert result["out"] == 2

    # Unconnected pins should be '?'
    assert result["in_minus"] == "?"
    assert result["vcc"] == "?"
    assert result["vee"] == "?"


def test_inverting_opamp_simple_netlist():
    """Ensure inverting-opamp-simple.asc produces the expected netlist."""
    examples_dir = Path(__file__).parent / "examples"
    asc_path = examples_dir / "inverting-opamp-simple.asc"

    lt = LTspice()
    lt.read(str(asc_path))
    lt.parse()
    lt.make_netlist()

    expected = """W 1 2; right
W 3 4; right
W 5 6; right
W 1 7; down
W 8 7; right
W 7 9; right
W 4 10; down
W 11 10; right
W 10 12; right
W 13 14; right
W 5 15; down
W 13 16; down
W 17 0_2; down
W 18 0_1; down
R1 6 8 1000.0; right
R2 2 3 5000.0; right
R3 16 18 833.0; down
Vin 15 17 {Vin}; down
E1 11 0 opamp 9 14
"""

    assert lt.netlist == expected
