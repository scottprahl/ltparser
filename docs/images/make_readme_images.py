#!/usr/bin/env python3
"""
Test script to verify all README examples work correctly.

This script tests each example circuit from the README to ensure
they parse correctly and generate valid netlists.

Usage:
    python test_readme_examples.py
"""

import sys
from pathlib import Path
import ltparser

examples_dir = "../../tests/examples/"

asc_files = ["passive_filter_band_pass", "amm_test_6", "twin_t", "voltage_divider_6", "volt_test_6", "inverting_opamp_simple"]


def create_image(name):
    """Create passive band_pass filter image."""
    print("creating image for", name)

    lt = ltparser.LTspice()
    lt.read(examples_dir + name + ".asc")
    cct = lt.circuit()
    cct.draw(name + ".png", scale=0.5)


def main():
    """Make all images."""
    for name in asc_files:
        create_image(name)


if __name__ == "__main__":
    sys.exit(main())
