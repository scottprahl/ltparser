"""
Tests for ltparser.components module
"""

from ltparser.components import node_key, rotate_point, ComponentMatcher


def test_node_key_positive():
    """Test node key generation with positive coordinates."""
    assert node_key(0, 0) == "0000_0000"
    assert node_key(100, 200) == "0100_0200"
    assert node_key(1234, 5678) == "1234_5678"


def test_node_key_negative():
    """Test node key generation with negative coordinates."""
    assert node_key(-10, -20) == "-010_-020"


def test_rotate_point_down():
    """Test point rotation with down/R0 orientation."""
    assert rotate_point(10, 20, "down") == (10, 20)


def test_rotate_point_left():
    """Test point rotation with left/R90 orientation."""
    assert rotate_point(10, 20, "left") == (-20, 10)


def test_rotate_point_up():
    """Test point rotation with up/R180 orientation."""
    assert rotate_point(10, 20, "up") == (-10, -20)


def test_rotate_point_right():
    """Test point rotation with right/R270 orientation."""
    assert rotate_point(10, 20, "right") == (20, -10)


def test_component_matcher_creation():
    """Test ComponentMatcher instantiation."""
    nodes = {"0000_0000": 0, "0100_0200": 1}
    matcher = ComponentMatcher(nodes)
    assert matcher.nodes == nodes


def test_match_opamp_nodes():
    """Test 5-pin op-amp node matching."""
    # Create simple test nodes at expected positions
    nodes = {
        "0000_0000": 1,  # Center
        "-032_-016": 2,  # in_minus (formatted with leading zeros)
        "-032_0016": 3,  # in_plus
        "0032_0000": 4,  # out
        "0000_-032": 5,  # vcc
        "0000_0032": 6,  # vee
    }

    matcher = ComponentMatcher(nodes)
    matched = matcher.match_opamp_nodes(0, 0, "down")

    assert "in_minus" in matched
    assert "in_plus" in matched
    assert "out" in matched
    assert "vcc" in matched
    assert "vee" in matched


def test_match_simple_opamp_nodes():
    """Test 3-pin op-amp node matching."""
    nodes = {
        "-032_0048": 1,  # in_plus
        "-032_0080": 2,  # in_minus
        "0032_0064": 3,  # out
    }

    matcher = ComponentMatcher(nodes)
    matched = matcher.match_simple_opamp_nodes(0, 0, "down")

    assert "in_plus" in matched
    assert "in_minus" in matched
    assert "out" in matched
