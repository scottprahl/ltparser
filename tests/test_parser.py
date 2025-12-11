"""
Unit tests for low-level parser helpers.

These tests focus on value parsing (SI prefixes, units, etc.).
"""

import pytest
from ltparser.netlist import _parse_prefixed_value


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("10", 10.0),
        ("3.3", 3.3),
        ("1e-3", 1e-3),
        ("  4  ", 4.0),
        # k, Meg, m
        ("10k", 1e4),
        ("1Meg", 1e6),
        ("1meg", 1e6),
        ("2M", 2e-3),  # 'm' is milli; 'M' falls back to plain number (2.0)
        # micro: u and µ
        ("3u", 3e-6),
        ("3µ", 3e-6),
        ("3uV", 3e-6),
        ("3µA", 3e-6),
        # nano, pico
        ("2n", 2e-9),
        ("2nF", 2e-9),
        ("5nA", 5e-9),
        ("7p", 7e-12),
        ("7pF", 7e-12),
        # milli with units
        ("1m", 1e-3),
        ("1mA", 1e-3),
        ("6mV", 6e-3),
        # exponent + prefix + unit
        ("-3.3e-2mA", -3.3e-5),
    ],
)
def test_parse_prefixed_value_valid(raw, expected):
    val = _parse_prefixed_value(raw)
    assert val == pytest.approx(expected)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        " ",
        "abc",
        "+",
        "-",
    ],
)
def test_parse_prefixed_value_invalid(raw):
    assert _parse_prefixed_value(raw) is None


# For backwards compatibility with unittest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
