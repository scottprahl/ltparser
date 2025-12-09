"""Tests for ltparser.transformations module."""

from ltparser.transformations import NetlistTransformer


def test_reorient_rlc_left_to_right():
    """Test reorienting left-facing components to right."""
    netlist = "W 1 2; left\n"
    result = NetlistTransformer.reorient_rlc(netlist)
    assert "; left" not in result
    assert "W 2 1; right" in result


def test_reorient_rlc_up_to_down():
    """Test reorienting up-facing components to down."""
    netlist = "W 3 4; up\n"
    result = NetlistTransformer.reorient_rlc(netlist)
    assert "; up" not in result
    assert "W 4 3; down" in result


def test_reorient_rlc_resistors():
    """Test reorienting resistors."""
    netlist = """R1 5 6 1000.0; left
R2 7 8 2000.0; up
R3 9 10 3000.0; right
"""
    result = NetlistTransformer.reorient_rlc(netlist)
    assert "; left" not in result
    assert "; up" not in result
    assert "R1 6 5 1000.0; right" in result
    assert "R2 8 7 2000.0; down" in result
    assert "R3 9 10 3000.0; right" in result  # Already right, unchanged


def test_renumber_nodes_sequential():
    """Test basic sequential node renumbering."""
    netlist = """W 5 3; right
W 3 2; right
R1 5 2 1000.0; right
"""
    result = NetlistTransformer.renumber_nodes_for_drawing(netlist)

    # Should renumber in order of appearance: 5->1, 3->2, 2->3
    assert "W 1 2; right" in result
    assert "W 2 3; right" in result
    assert "R1 1 3 1000.0; right" in result


def test_renumber_nodes_single_ground_occurrence():
    """Test renumbering with only one ground occurrence stays as 0."""
    netlist = """W 3 2; right
W 5 4; down
R1 2 0 1000.0; down
"""
    result = NetlistTransformer.renumber_nodes_for_drawing(netlist)

    # When ground appears only once, it stays as plain 0
    assert " 0 " in result or " 0;" in result or " 0\n" in result
    assert "0_1" not in result
    assert "0_2" not in result
    # Other nodes renumbered sequentially
    assert "W 1 2; right" in result


def test_renumber_nodes_coincident_grounds():
    """Test renumbering with two grounds at same location (treated as single ground)."""
    # Create mock parsed data with two FLAG statements at same location
    parsed_data = [
        [["FLAG", 100, 200, "0"]],  # Ground at (100, 200)
        [["FLAG", 100, 200, "0"]],  # Same ground location
    ]

    netlist = """W 3 2; right
W 5 0; down
R1 2 0 1000.0; down
"""
    result = NetlistTransformer.renumber_nodes_for_drawing(netlist, parsed_data)

    # Both grounds at same location → treated as single ground → stays as 0
    assert " 0;" in result or " 0 " in result or " 0\n" in result
    # Should appear twice (two components connected to same ground)
    ground_count = result.count(" 0;") + result.count(" 0 ") + result.count(" 0\n")
    assert ground_count >= 2
    # No numbered grounds
    assert "0_1" not in result
    assert "0_2" not in result


def test_renumber_nodes_separate_grounds():
    """Test renumbering with two grounds at different locations (separate grounds)."""
    # Create mock parsed data with two FLAG statements at different locations
    parsed_data = [
        [["FLAG", 100, 200, "0"]],  # Ground at (100, 200)
        [["FLAG", 300, 400, "0"]],  # Ground at different location (300, 400)
    ]

    netlist = """W 3 2; right
W 5 0; down
R1 2 0 1000.0; down
"""
    result = NetlistTransformer.renumber_nodes_for_drawing(netlist, parsed_data)

    # Two grounds at different locations → each gets unique ID
    assert "0_1" in result
    assert "0_2" in result
    # No plain 0
    plain_ground_count = result.count(" 0;") + result.count(" 0 ") + result.count(" 0\n")
    assert plain_ground_count == 0
    # Nodes renumbered sequentially
    assert "W 1 2; right" in result


def test_renumber_nodes_multiple_grounds_no_parsed_data():
    """Test renumbering multiple grounds without parsed data (fallback behavior)."""
    netlist = """W 3 2; right
W 5 0; down
R1 2 0 1000.0; down
"""
    # No parsed_data → fallback to counting occurrences
    result = NetlistTransformer.renumber_nodes_for_drawing(netlist, None)

    # Without location data, multiple occurrences → each gets unique ID
    assert "0_1" in result
    assert "0_2" in result
    # Nodes renumbered sequentially
    assert "W 1 2; right" in result


def test_convert_named_nodes():
    """Test converting named nodes to numbers."""
    netlist = """W +Vs 1; right
W -Vs 2; right
R1 1 2 1000.0; right
"""

    nodes = {
        "0000_0000": "+Vs",
        "0100_0000": "-Vs",
        "0200_0000": 1,
        "0300_0000": 2,
    }

    result_netlist, result_nodes = NetlistTransformer.convert_named_nodes_to_numbers(netlist, nodes)

    # Named nodes should be converted to numbers
    assert "+Vs" not in result_netlist
    assert "-Vs" not in result_netlist

    # Should have numeric replacements
    assert all(isinstance(v, int) or v == "0" for v in result_nodes.values())
