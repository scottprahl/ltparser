"""
Test IOPIN/port generation functionality.

Tests that ltparser correctly generates port definitions from IOPIN/FLAG pairs.
"""

import pytest
from pathlib import Path

import ltparser

EXAMPLES_DIR = Path(__file__).parent / "examples"


def test_voltage_divider_with_ports():
    """Test that voltage_divider_1.asc generates correct netlist with ports."""
    asc_path = EXAMPLES_DIR / "voltage_divider_1.asc"

    expected_netlist = """W 1 2; right
W 2 3; right
W 2 4; down
W 1 5; down
W 6 7; down
W 7 8; right
W 7 9; down
W 10 11; down
W 12 13; down
W 11 13; right
W 11 0; down
V 5 10 10; down
R1 4 6 8.0; down
R2 9 12 2.0; down
P1 8 0; down, v=A
P2 3 0; down, v=B
"""

    lt = ltparser.LTspice()
    lt.read(str(asc_path))
    netlist = lt.make_netlist()

    # Normalize whitespace for comparison
    expected_lines = [line.strip() for line in expected_netlist.strip().split("\n") if line.strip()]
    actual_lines = [line.strip() for line in netlist.strip().split("\n") if line.strip()]

    # Check line count
    assert len(actual_lines) == len(expected_lines), (
        f"Expected {len(expected_lines)} lines, got {len(actual_lines)}\n"
        f"Expected:\n{expected_netlist}\n"
        f"Actual:\n{netlist}"
    )

    # Check each line
    for i, (expected, actual) in enumerate(zip(expected_lines, actual_lines), 1):
        assert actual == expected, (
            f"Line {i} mismatch:\n"
            f"  Expected: {expected}\n"
            f"  Actual:   {actual}\n"
            f"\nFull expected netlist:\n{expected_netlist}\n"
            f"\nFull actual netlist:\n{netlist}"
        )

    print("✓ Netlist matches expected output")


def test_voltage_divider_port_count():
    """Test that voltage_divider_1.asc generates exactly 2 ports."""
    asc_path = EXAMPLES_DIR / "voltage_divider_1.asc"
    lt = ltparser.LTspice()
    lt.read(str(asc_path))
    netlist = lt.make_netlist()

    # Count port lines (start with P followed by digit)
    port_lines = [
        line for line in netlist.split("\n") if line.strip().startswith("P") and line.strip()[1].isdigit()
    ]

    assert len(port_lines) == 2, f"Expected 2 ports, found {len(port_lines)}: {port_lines}"
    print(f"✓ Found {len(port_lines)} ports")


def test_voltage_divider_port_labels():
    """Test that voltage_divider_1.asc ports have correct labels from FLAGs."""
    asc_path = EXAMPLES_DIR / "voltage_divider_1.asc"
    lt = ltparser.LTspice()
    lt.read(str(asc_path))
    netlist = lt.make_netlist()

    # Extract port lines
    port_lines = [
        line.strip()
        for line in netlist.split("\n")
        if line.strip().startswith("P") and line.strip()[1].isdigit()
    ]

    # Check that both ports have labels from FLAGs (A and B), not default PORT_x_y labels
    assert any("v=A" in line for line in port_lines), f"Port with label 'A' not found. Ports: {port_lines}"
    assert any("v=B" in line for line in port_lines), f"Port with label 'B' not found. Ports: {port_lines}"

    # Check that no default labels are used
    assert not any(
        "PORT_" in line for line in port_lines
    ), f"Default PORT_ label found (FLAG matching failed). Ports: {port_lines}"

    print("✓ Both ports have correct FLAG labels (A and B)")


def test_voltage_divider_port_format():
    """Test that ports follow the lcapy format: P{n} {node} 0; down, v={label}."""
    asc_path = EXAMPLES_DIR / "voltage_divider_1.asc"
    lt = ltparser.LTspice()
    lt.read(str(asc_path))
    netlist = lt.make_netlist()

    port_lines = [
        line.strip()
        for line in netlist.split("\n")
        if line.strip().startswith("P") and line.strip()[1].isdigit()
    ]

    import re

    # Pattern: P{number} {node} 0; down, v={label}
    pattern = r"^P\d+\s+\d+\s+0;\s+down,\s+v=\w+$"

    for port in port_lines:
        assert re.match(pattern, port), f"Port format incorrect: '{port}'"

    print("✓ All ports follow correct lcapy format")


def test_passive_filter_with_port():
    """Test that passive_filter_band_pass.asc generates correct port."""
    asc_path = EXAMPLES_DIR / "passive_filter_low_pass.asc"
    lt = ltparser.LTspice()
    lt.read(str(asc_path))
    netlist = lt.make_netlist()

    # Should have exactly 1 port with label 'Vo'
    port_lines = [
        line.strip()
        for line in netlist.split("\n")
        if line.strip().startswith("P") and line.strip()[1].isdigit()
    ]

    assert len(port_lines) == 1, f"Expected 1 port, found {len(port_lines)}: {port_lines}"
    assert "v=Vo" in port_lines[0], f"Port should have label 'Vo', got: {port_lines[0]}"

    print(f"✓ Passive filter has correct port: {port_lines[0]}")


def test_no_iopins_no_ports():
    """Test that files without IOPINs don't generate port lines."""
    asc_path = EXAMPLES_DIR / "simple3.asc"

    lt = ltparser.LTspice()
    lt.read(str(asc_path))
    netlist = lt.make_netlist()

    port_lines = [
        line for line in netlist.split("\n") if line.strip().startswith("P") and line.strip()[1].isdigit()
    ]

    assert len(port_lines) == 0, f"Expected no ports, found {len(port_lines)}: {port_lines}"


# For backwards compatibility with unittest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
