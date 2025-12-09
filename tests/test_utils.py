"""Tests for ltparser.utils module."""

from ltparser.utils import clean_node_name, parse_direction, format_value, is_ground_node


def test_clean_node_name():
    """Test node name cleaning."""
    assert clean_node_name("5") == "5"
    assert clean_node_name("5;") == "5"
    assert clean_node_name("10;") == "10"
    assert clean_node_name("0_1;") == "0_1"


def test_parse_direction_with_semicolon():
    """Test direction parsing from lines with semicolons."""
    line1 = "W 1 2; right"
    main1, dir1 = parse_direction(line1)
    assert main1 == "W 1 2"
    assert dir1 == "right"

    line3 = "R1 3 4 1000.0; down"
    main3, dir3 = parse_direction(line3)
    assert main3 == "R1 3 4 1000.0"
    assert dir3 == "down"


def test_parse_direction_without_semicolon():
    """Test direction parsing from lines without semicolons."""
    line2 = "W 1 2"
    main2, dir2 = parse_direction(line2)
    assert main2 == "W 1 2"
    assert dir2 is None


def test_format_value():
    """Test value formatting."""
    assert format_value(1000) == "1000"
    assert format_value(1000.0) == "1000.0"
    assert format_value("1k") == "1k"
    assert format_value("{Vin}") == "{Vin}"


def test_is_ground_node_numeric():
    """Test ground node detection with numeric values."""
    assert is_ground_node(0)
    assert not is_ground_node(1)
    assert not is_ground_node(5)


def test_is_ground_node_string():
    """Test ground node detection with string values."""
    assert is_ground_node("0")
    assert is_ground_node("0_1")
    assert is_ground_node("0_2")
    assert not is_ground_node("1")
    assert not is_ground_node("5")
