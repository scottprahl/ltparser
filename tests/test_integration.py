"""
Integration tests for ltparser with real LTspice files.

These tests use actual .asc files to verify end-to-end functionality.
"""

import os
import ltparser


# Get the path to the examples directory
EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "examples")


def test_simple1_with_renumbering():
    """Test simple1.asc with default renumbering."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "simple1.asc"))
    lt.parse()
    lt.make_netlist()

    expected = """W 1 2; right
W 1 3; down
W 2 4; down
W 5 6; down
W 7 8; down
W 6 8; right
W 6 0; down
V1 3 5 5; down
R1 4 7 1000.0; down
"""

    # Normalize whitespace for comparison
    actual_lines = [line.strip() for line in lt.netlist.strip().split("\n")]
    expected_lines = [line.strip() for line in expected.strip().split("\n")]

    # Check line count
    assert len(actual_lines) == len(
        expected_lines
    ), f"Expected {len(expected_lines)} lines, got {len(actual_lines)}"

    # Check each line
    for i, (actual, expected_line) in enumerate(zip(actual_lines, expected_lines)):
        assert (
            actual == expected_line
        ), f"Line {i+1} mismatch:\n  Expected: {expected_line}\n  Got:      {actual}"

    # Check no leading spaces
    for line in lt.netlist.split("\n"):
        if line:  # Skip empty lines
            assert line[0] != " ", f"Line has leading space: '{line}'"

    # Check no unknown nodes
    assert "?" not in lt.netlist, "Netlist contains unknown nodes (?)"

    # Check ground node is present
    assert " 0;" in lt.netlist or " 0 " in lt.netlist, "Should have ground node (0)"


def test_simple1_without_renumbering():
    """Test simple1.asc without renumbering to verify coordinate-based node matching."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "simple1.asc"))
    lt.parse()
    lt.make_netlist(renumber_nodes=False)

    # Should have no unknown nodes
    assert "?" not in lt.netlist, f"Netlist contains unknown nodes (?):\n{lt.netlist}"

    # Should have wires
    assert "W " in lt.netlist, "Netlist should contain wires"

    # Should have voltage source
    assert "V1" in lt.netlist, "Netlist should contain V1"

    # Should have resistor
    assert "R1" in lt.netlist, "Netlist should contain R1"

    # Check no leading spaces
    for line in lt.netlist.split("\n"):
        if line:  # Skip empty lines
            assert line[0] != " ", f"Line has leading space: '{line}'"

    # Verify nodes dictionary has coordinate keys (not numeric)
    # After make_netlist without renumbering, should have coordinate keys
    assert any(
        "_" in str(k) for k in lt.nodes.keys()
    ), f"Expected coordinate keys (with '_'), got: {list(lt.nodes.keys())[:5]}"


def test_simple1_multiple_calls():
    """Test that multiple calls to make_netlist work correctly."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "simple1.asc"))
    lt.parse()

    # First call with renumbering
    lt.make_netlist()
    netlist1 = lt.netlist
    assert "?" not in netlist1, "First call: netlist contains unknown nodes"

    # Second call without renumbering
    lt.read(os.path.join(EXAMPLES_DIR, "simple1.asc"))
    lt.parse()
    lt.make_netlist(renumber_nodes=False)
    netlist2 = lt.netlist
    assert "?" not in netlist2, "Second call: netlist contains unknown nodes"

    # Third call with renumbering again
    lt.read(os.path.join(EXAMPLES_DIR, "simple1.asc"))
    lt.parse()
    lt.make_netlist()
    netlist3 = lt.netlist
    assert "?" not in netlist3, "Third call: netlist contains unknown nodes"


def test_simple1_parse_required():
    """Test that parse() must be called before make_netlist()."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "simple1.asc"))

    # Should work - make_netlist calls parse if needed
    lt.make_netlist()
    assert lt.parsed is not None, "parse() should have been called automatically"
    assert "?" not in lt.netlist, "Netlist should be valid"


def test_simple1_component_values():
    """Test that component values are correctly extracted."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "simple1.asc"))
    lt.parse()
    lt.make_netlist()

    # Check voltage source value (V suffix should be removed)
    assert "5V" not in lt.netlist, "Voltage source should not have 'V' suffix"
    assert "V1 3 5 5" in lt.netlist, "V1 should have value 5 (not 5V)"

    # Check resistor value (should be converted to float)
    assert "1000.0" in lt.netlist or "1000" in lt.netlist, "Resistor should have 1000.0 value"


def test_simple0_unit_conversion():
    """Test simple0.asc with Meg unit conversion."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "simple0.asc"))
    lt.parse()
    lt.make_netlist()

    expected = """W 1 2; right
W 3 4; right
W 3 0; down
V1 1 3 3.3; down
R1 2 4 4700000.0; down
"""

    # Normalize whitespace for comparison
    actual_lines = [line.strip() for line in lt.netlist.strip().split("\n")]
    expected_lines = [line.strip() for line in expected.strip().split("\n")]

    # Check line count
    assert len(actual_lines) == len(
        expected_lines
    ), f"Expected {len(expected_lines)} lines, got {len(actual_lines)}"

    # Check each line
    for i, (actual, expected_line) in enumerate(zip(actual_lines, expected_lines)):
        assert (
            actual == expected_line
        ), f"Line {i+1} mismatch:\n  Expected: {expected_line}\n  Got:      {actual}"

    # Check that Meg is converted to numeric
    assert "Meg" not in lt.netlist, "Should convert 'Meg' to numeric value"

    # Check V1 value (no V suffix)
    assert "3.3V" not in lt.netlist, "V1 should not have 'V' suffix"
    assert "V1 1 3 3.3" in lt.netlist, "V1 should have value 3.3"

    # Check R1 value converted from Meg
    r1_line = [line for line in lt.netlist.split("\n") if "R1" in line][0]
    assert (
        "4700000" in r1_line or "4.7e+06" in r1_line
    ), f"R1 should have 4.7Meg converted to 4700000.0, got: {r1_line}"

    # Check no leading spaces
    for line in lt.netlist.split("\n"):
        if line:  # Skip empty lines
            assert line[0] != " ", f"Line has leading space: '{line}'"

    # Check ground node is present
    assert " 0;" in lt.netlist or " 0 " in lt.netlist, "Should have ground node (0)"


def test_simple0_direction_conversion():
    """Test that R0 direction is converted to 'down' for simple0.asc."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "simple0.asc"))
    lt.parse()
    lt.make_netlist()

    # Both components should have 'down' direction
    v1_line = [line for line in lt.netlist.split("\n") if "V1" in line][0]
    r1_line = [line for line in lt.netlist.split("\n") if "R1" in line][0]

    assert "; down" in v1_line, f"V1 should have 'down' direction, got: {v1_line}"
    assert "; down" in r1_line, f"R1 should have 'down' direction, got: {r1_line}"


def test_simple2_multiple_grounds():
    """Test simple2.asc with two separate ground nodes."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "simple2.asc"))
    lt.parse()
    lt.make_netlist(renumber_nodes=False)

    # Should have two separate grounds: 0_1 and 0_2
    assert "0_1" in lt.netlist, "Should have ground 0_1"
    assert "0_2" in lt.netlist, "Should have ground 0_2"

    # Should NOT have plain '0' (that's for single grounds only)
    # But check carefully - '0_1' and '0_2' contain '0'
    lines_with_plain_zero = []
    for line in lt.netlist.split("\n"):
        if line.strip():
            # Check for ' 0;' or ' 0 ' or ' 0\n' (plain zero, not part of 0_1 or 0_2)
            if " 0;" in line or line.endswith(" 0"):
                # Make sure it's not ' 0_1' or ' 0_2'
                if "0_1" not in line and "0_2" not in line:
                    lines_with_plain_zero.append(line)

    assert (
        len(lines_with_plain_zero) == 0
    ), f"Should not have plain '0' ground (use 0_1, 0_2), found: {lines_with_plain_zero}"

    # Check V1 and R1 each connect to different grounds
    v1_line = [line for line in lt.netlist.split("\n") if "V1" in line][0]
    r1_line = [line for line in lt.netlist.split("\n") if "R1" in line][0]

    # One should have 0_1, the other 0_2
    assert ("0_1" in v1_line and "0_2" in r1_line) or (
        "0_2" in v1_line and "0_1" in r1_line
    ), f"V1 and R1 should connect to different grounds\n  V1: {v1_line}\n  R1: {r1_line}"

    # Check no unknown nodes
    assert "?" not in lt.netlist, f"Netlist should not have unknown nodes:\n{lt.netlist}"


def test_simple2_conversion_no_renumbering():
    """Test simple2.asc with Meg unit conversion."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "simple2.asc"))
    lt.parse()
    lt.make_netlist(renumber_nodes=False)

    expected = """W 2 1; right
W 2 3; down
W 1 4; down
V1 3 0_1 5; down
R1 4 0_2 1000.0; down
"""
    assert lt.netlist == expected


def test_simple2_conversion():
    """Test simple2.asc with Meg unit conversion."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "simple2.asc"))
    lt.parse()
    lt.make_netlist()

    expected = """W 1 2; right
W 1 3; down
W 2 4; down
V1 3 0_1 5; down
R1 4 0_2 1000.0; down
"""
    assert lt.netlist == expected


def test_resonant_series():
    """Test resonant-series.asc: µ parsing, milli-H, and AC source."""
    lt = ltparser.LTspice()
    lt.read(os.path.join(EXAMPLES_DIR, "resonant_series.asc"))
    lt.parse()
    lt.make_netlist()

    expected = """W 1 2; right
W 3 4; right
W 4 5; down
W 1 6; down
W 7 8; down
W 9 0; down
W 10 11; down
W 0 11; right
R1 2 3 2.0; right
L1 5 7 0.001; down
C1 8 10 4e-07; down
V 6 9 ac 20.000000; down
"""

    assert lt.netlist == expected
