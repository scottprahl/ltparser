"""
Legacy tests from original ltparser.py, updated for refactored code.

These tests verify value parsing and bulk file processing across many example circuits.
"""

from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None

from ltparser import LTspice
from ltparser.netlist import _parse_prefixed_value


# List of example circuits to test
LTSPICE_FILES = [
    "orientation_test.asc",
    "orientation_test2.asc",
    "passive_crossover.asc",
    "passive_filter_band_block.asc",
    "passive_filter_band_pass.asc",
    "passive_filter_high_pass.asc",
    "passive_filter_low_pass_omega.asc",
    "passive_filter_low_pass.asc",
    "passive_filter_low_with_load.asc",
    "resonant_series.asc",
    "simple0.asc",
    "simple1.asc",
    "simple2.asc",
    "simple3.asc",
    "twin_t.asc",
]

# Get examples directory
EXAMPLES_DIR = Path(__file__).parent / "examples"


class TestValueParsing:
    """Tests for value parsing with SI prefixes and units."""

    def test_integers(self):
        """Parse simple integers."""
        assert _parse_prefixed_value("100000") == pytest.approx(100000)
        assert _parse_prefixed_value("12") == pytest.approx(12)
        assert _parse_prefixed_value("0") == pytest.approx(0)
        assert _parse_prefixed_value("-12") == pytest.approx(-12)
        assert _parse_prefixed_value("-100000") == pytest.approx(-100000)

    def test_reals(self):
        """Parse simple reals."""
        assert _parse_prefixed_value("12.01") == pytest.approx(12.01)
        assert _parse_prefixed_value("0.01") == pytest.approx(0.01)
        assert _parse_prefixed_value(".01") == pytest.approx(0.01)
        assert _parse_prefixed_value("12.") == pytest.approx(12)
        assert _parse_prefixed_value("-12.01") == pytest.approx(-12.01)
        assert _parse_prefixed_value("-0.01") == pytest.approx(-0.01)
        assert _parse_prefixed_value("-.01") == pytest.approx(-0.01)
        assert _parse_prefixed_value("-12.") == pytest.approx(-12)

    def test_integer_with_si_prefix(self):
        """Integers with SI prefix suffixes."""
        assert _parse_prefixed_value("12f") == pytest.approx(12e-15)
        assert _parse_prefixed_value("12p") == pytest.approx(12e-12)
        assert _parse_prefixed_value("12n") == pytest.approx(12e-9)
        assert _parse_prefixed_value("12u") == pytest.approx(12e-6)
        assert _parse_prefixed_value("12m") == pytest.approx(12e-3)
        assert _parse_prefixed_value("12k") == pytest.approx(12e3)
        assert _parse_prefixed_value("12meg") == pytest.approx(12e6)

    def test_real_with_si_prefix(self):
        """Reals with SI prefix suffixes."""
        assert _parse_prefixed_value("4.7f") == pytest.approx(4.7e-15)
        assert _parse_prefixed_value("4.7p") == pytest.approx(4.7e-12)
        assert _parse_prefixed_value("4.7n") == pytest.approx(4.7e-9)
        assert _parse_prefixed_value("4.7u") == pytest.approx(4.7e-6)
        assert _parse_prefixed_value("4.7m") == pytest.approx(4.7e-3)
        assert _parse_prefixed_value("4.7k") == pytest.approx(4.7e3)
        assert _parse_prefixed_value("4.7meg") == pytest.approx(4.7e6)


class TestBulkFileProcessing:
    """Test that all example circuits can be read, parsed, and converted to netlists."""

    @pytest.mark.parametrize("filename", LTSPICE_FILES)
    def test_file_opening(self, filename):
        """Validate that all example files can be opened."""
        filepath = EXAMPLES_DIR / filename

        if not filepath.exists():
            pytest.skip(f"Example file not found: {filename}")

        lt = LTspice()
        lt.read(str(filepath))
        assert lt.contents is not None, f"Failed to read {filename}"

    @pytest.mark.parametrize("filename", LTSPICE_FILES)
    def test_file_parsing(self, filename):
        """Validate that all example files can be parsed."""
        filepath = EXAMPLES_DIR / filename

        if not filepath.exists():
            pytest.skip(f"Example file not found: {filename}")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        assert lt.parsed is not None, f"Failed to parse {filename}"
        assert len(lt.parsed) > 0, f"Parsed data is empty for {filename}"

    @pytest.mark.parametrize("filename", LTSPICE_FILES)
    def test_netlist_generation(self, filename):
        """Validate that all example files can generate netlists."""
        filepath = EXAMPLES_DIR / filename

        if not filepath.exists():
            pytest.skip(f"Example file not found: {filename}")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        netlist = lt.make_netlist()

        assert netlist is not None, f"Netlist generation failed for {filename}"
        assert len(netlist) > 0, f"Generated netlist is empty for {filename}"

        # Basic sanity checks
        assert "?" not in netlist, f"Netlist has unmatched nodes (?) in {filename}"

    @pytest.mark.parametrize("filename", LTSPICE_FILES)
    def test_circuit_creation(self, filename):
        """Validate that all example files can create lcapy Circuit objects."""
        filepath = EXAMPLES_DIR / filename

        if not filepath.exists():
            pytest.skip(f"Example file not found: {filename}")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        lt.make_netlist()

        try:
            circuit = lt.circuit()
            # If lcapy is installed, verify circuit was created
            assert circuit is not None, f"Circuit creation returned None for {filename}"
        except ImportError:
            pytest.skip("lcapy not installed")


class TestSpecificCircuits:
    """Tests for specific circuit configurations."""

    def test_simple_circuit(self):
        """Simple circuit with voltage source and resistor."""
        filepath = EXAMPLES_DIR / "simple1.asc"
        if not filepath.exists():
            pytest.skip("simple1.asc not found")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()

        assert lt.parsed is not None
        assert len(lt.parsed) > 0

    def test_orientation_test(self):
        """Circuit to ensure symbol orientations are correct."""
        filepath = EXAMPLES_DIR / "orientation-test.asc"
        if not filepath.exists():
            pytest.skip("orientation_test.asc not found")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        netlist = lt.make_netlist()

        # Should have components in different orientations
        assert "; right" in netlist or "; left" in netlist or "; up" in netlist or "; down" in netlist

    def test_orientation_test2(self):
        """Second circuit to ensure symbol orientations are correct."""
        filepath = EXAMPLES_DIR / "orientation_test2.asc"
        if not filepath.exists():
            pytest.skip("orientation_test2.asc not found")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        netlist = lt.make_netlist()

        assert netlist is not None

    def test_low_pass_filter(self):
        """Passive low pass filter."""
        filepath = EXAMPLES_DIR / "passive_filter_low_pass.asc"
        if not filepath.exists():
            pytest.skip("passive_filter_low_pass.asc not found")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        netlist = lt.make_netlist()

        # Should have R, C, and voltage source
        assert "R" in netlist
        assert "C" in netlist
        assert "V" in netlist or "I" in netlist

    def test_low_pass_filter_with_load(self):
        """Passive low pass filter with load resistor."""
        filepath = EXAMPLES_DIR / "passive_filter_low_with_load.asc"
        if not filepath.exists():
            pytest.skip("passive_filter_low_with_load.asc not found")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        netlist = lt.make_netlist()

        # Should have multiple resistors
        resistor_count = netlist.count("R")
        assert resistor_count >= 2, "Should have at least 2 resistors (source + load)"

    def test_high_pass_filter(self):
        """Passive high pass filter."""
        filepath = EXAMPLES_DIR / "passive_filter_high_pass.asc"
        if not filepath.exists():
            pytest.skip("passive_filter_high_pass.asc not found")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        netlist = lt.make_netlist()

        assert "R" in netlist
        assert "C" in netlist

    def test_band_pass_filter(self):
        """Passive band pass filter."""
        filepath = EXAMPLES_DIR / "passive_filter_band_pass.asc"
        if not filepath.exists():
            pytest.skip("passive_filter_band_pass.asc not found")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        netlist = lt.make_netlist()

        assert netlist is not None

    def test_band_block_filter(self):
        """Passive band block (notch) filter."""
        filepath = EXAMPLES_DIR / "passive_filter_band_block.asc"
        if not filepath.exists():
            pytest.skip("passive_filter_band_block.asc not found")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        netlist = lt.make_netlist()

        assert netlist is not None

    def test_series_resonant(self):
        """Resonant series circuit."""
        filepath = EXAMPLES_DIR / "resonant_series.asc"
        if not filepath.exists():
            pytest.skip("resonant_series.asc not found")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        netlist = lt.make_netlist()

        # Should have R, L, C
        assert "R" in netlist
        assert "L" in netlist
        assert "C" in netlist

    def test_circuit_with_parameters(self):
        """Circuit with parameterized values."""
        filepath = EXAMPLES_DIR / "passive_filter_low_pass_omega.asc"
        if not filepath.exists():
            pytest.skip("passive_filter_low_pass_omega.asc not found")

        lt = LTspice()
        lt.read(str(filepath))
        lt.parse()
        netlist = lt.make_netlist()

        # Should have components
        assert len(netlist) > 0


# For backwards compatibility with unittest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
