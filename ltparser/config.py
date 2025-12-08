"""
Configuration management for ltparser.

Handles loading and accessing component configuration data.
"""

import json
import os


def load_components_config():
    """
    Load components configuration from JSON file.

    Returns:
        dict: Component configuration dictionary
    """
    # Try to find components_config.json in the same directory as this file
    config_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(config_dir, "components_config.json")

    if not os.path.exists(config_path):
        # Try parent directory
        config_path = os.path.join(os.path.dirname(config_dir), "components_config.json")

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)

    # Return empty config if file not found
    return {}


# Load configuration on module import
COMPONENTS_CONFIG = load_components_config()
