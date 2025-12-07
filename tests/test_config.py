"""
Tests for ltparser.config module
"""

from ltparser.config import load_components_config, COMPONENTS_CONFIG


def test_load_components_config():
    """Test that components config loads correctly."""
    config = load_components_config()

    # Should return a dict
    assert isinstance(config, dict), f"Expected dict, got {type(config)}"


def test_components_config_is_dict():
    """Test that COMPONENTS_CONFIG is a dictionary."""
    assert isinstance(COMPONENTS_CONFIG, dict)


def test_components_config_structure():
    """Test that COMPONENTS_CONFIG has expected structure."""
    if COMPONENTS_CONFIG:
        # If config is loaded, it should have 'components' key
        assert "components" in COMPONENTS_CONFIG, "Config should have 'components' key"

        # Check that components has expected sub-keys
        components = COMPONENTS_CONFIG["components"]
        assert (
            "two_terminal" in components or "multi_terminal" in components
        ), "Components should have 'two_terminal' or 'multi_terminal'"
