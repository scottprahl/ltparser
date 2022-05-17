#! /usr/bin/env python3
# pylint: disable=invalid-name
# pylint: disable=unused-variable
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=line-too-long

import unittest
import numpy as np
import ltparser

class LTspiceValues(unittest.TestCase):

    def test_01_integers(self):
        """Parse simple integers."""
        value = ltparser.ltspice_value_to_number("100000")
        self.assertAlmostEqual(value, 100000, delta=0.00001)
        value = ltparser.ltspice_value_to_number("12")
        self.assertAlmostEqual(value, 12, delta=0.00001)
        value = ltparser.ltspice_value_to_number("0")
        self.assertAlmostEqual(value, 0, delta=0.00001)
        value = ltparser.ltspice_value_to_number("-12")
        value = float(value)
        self.assertAlmostEqual(value, -12, delta=0.00001)
        value = ltparser.ltspice_value_to_number("-100000")
        value = float(value)
        self.assertAlmostEqual(value, -100000, delta=0.00001)

    def test_02_reals(self):
        """Parse simple reals."""
        value = ltparser.ltspice_value_to_number("12.01")
        self.assertAlmostEqual(value, 12.01, delta=0.00001)
        value = ltparser.ltspice_value_to_number("0.01")
        self.assertAlmostEqual(value, 0.01, delta=0.00001)
        value = ltparser.ltspice_value_to_number(".01")
        self.assertAlmostEqual(value, 0.01, delta=0.00001)
        value = ltparser.ltspice_value_to_number("12.")
        self.assertAlmostEqual(value, 12, delta=0.00001)
        value = ltparser.ltspice_value_to_number("-12.01")
        value = float(value)
        self.assertAlmostEqual(value, -12.01, delta=0.00001)
        value = ltparser.ltspice_value_to_number("-0.01")
        value = float(value)
        self.assertAlmostEqual(value, -0.01, delta=0.00001)
        value = ltparser.ltspice_value_to_number("-.01")
        value = float(value)
        self.assertAlmostEqual(value, -0.01, delta=0.00001)
        value = ltparser.ltspice_value_to_number("-12.")
        value = float(value)
        self.assertAlmostEqual(value, -12, delta=0.00001)

    def test_integer_mixed(self):
        value = ltparser.ltspice_value_to_number("12f")
        self.assertAlmostEqual(value, 12e-15)
        value = ltparser.ltspice_value_to_number("12p")
        self.assertAlmostEqual(value, 12e-12)
        value = ltparser.ltspice_value_to_number("12n")
        self.assertAlmostEqual(value, 12e-9)
        value = ltparser.ltspice_value_to_number("12u")
        self.assertAlmostEqual(value, 12e-6)
        value = ltparser.ltspice_value_to_number("12m")
        self.assertAlmostEqual(value, 12e-3)
        value = ltparser.ltspice_value_to_number("12k")
        self.assertAlmostEqual(value, 12e3)
        value = ltparser.ltspice_value_to_number("12meg")
        self.assertAlmostEqual(value, 12e6)

    def test_real_mixed(self):
        value = ltparser.ltspice_value_to_number("4.7f")
        self.assertAlmostEqual(value, 4.7e-15)
        value = ltparser.ltspice_value_to_number("4.7p")
        self.assertAlmostEqual(value, 4.7e-12)
        value = ltparser.ltspice_value_to_number("4.7n")
        self.assertAlmostEqual(value, 4.7e-9)
        value = ltparser.ltspice_value_to_number("4.7u")
        self.assertAlmostEqual(value, 4.7e-6)
        value = ltparser.ltspice_value_to_number("4.7m")
        self.assertAlmostEqual(value, 4.7e-3)
        value = ltparser.ltspice_value_to_number("4.7k")
        self.assertAlmostEqual(value, 4.7e3)
        value = ltparser.ltspice_value_to_number("4.7meg")
        self.assertAlmostEqual(value, 4.7e6)

ltspice_files = [
        "orientation-test.asc",
        "orientation-test2.asc",
        "passive-crossover.asc",
        "passive-filter-band-block.asc",
        "passive-filter-band-pass.asc",
        "passive-filter-high-pass.asc",
        "passive-filter-low-pass-omega.asc",
        "passive-filter-low-pass.asc",
        "passive-filter-low-with-load.asc",
        "resonant-series.asc",
        "simple0.asc",
        "simple1.asc",
        "simple2.asc",
        "twin-t.asc",
        ]

class Netlist(unittest.TestCase):
    def test_01_opening(self):
        """Validate that all ltspice test files open."""
        for fn in ltspice_files:
            lt = ltparser.LTspice()
            lt.read('tests/ltspice/' + fn)

    def test_02_parsing(self):
        """Validate that all ltspice test files parse."""
        for fn in ltspice_files:
            lt = ltparser.LTspice()
            lt.read('tests/ltspice/' + fn)
            lt.parse()

    def test_03_netlist(self):
        """Validate that all ltspice test files convert to netlists."""
        for fn in ltspice_files:
            lt = ltparser.LTspice()
            lt.read('tests/ltspice/' + fn)
            lt.make_netlist()

    def test_04_circuits(self):
        """Validate that all ltspice test files convert to circuits."""
        for fn in ltspice_files:
            lt = ltparser.LTspice()
            lt.read('tests/ltspice/' + fn)
            lt.make_netlist()
            cct = lt.circuit()

class ParserRLC(unittest.TestCase):
    def test_01_simple(self):
        """Simple circuit with voltage source and resistor."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"simple1.asc")
        lt.parse()

    def test_02_simple_with_ground(self):
        """Simple circuit with resistor with multiple grounds."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"simple1.asc")
        lt.parse()

    def test_03_orientation(self):
        """Circuit to ensure symbol orientations are correct."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"orientation-test.asc")
        lt.parse()

    def test_04_orientation(self):
        """Circuit to ensure symbol orientations are correct."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"orientation-test2.asc")
        lt.parse()

    def test_05_low_pass_filter(self):
        """Passive low pass filter."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"passive-filter-low-pass.asc")
        lt.parse()

    def test_06_low_pass_filter(self):
        """Passive low pass filter but with a load."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"passive-filter-low-with-load.asc")
        lt.parse()

    def test_06_low_pass_filter(self):
        """Passive low pass filter but with a load."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"passive-filter-low-with-load.asc")
        lt.parse()

    def test_07_high_pass_filter(self):
        """Passive low pass filter but with a load."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"passive-filter-high-pass.asc")
        lt.parse()

    def test_08_band_pass_filter(self):
        """Passive low pass filter but with a load."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
#        lt.read(path +"passive-filter-band-pass.asc")
#        lt.parse()

    def test_09_band_block_filter(self):
        """Passive low pass filter but with a load."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"passive-filter-band-block.asc")
        lt.parse()

    def test_10_series_resonant(self):
        """Resonant series circuit."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"resonant-series.asc")
        lt.parse()

    def test_11_circuit_with_param(self):
        """Passive low pass filter but with a load."""
        path = 'tests/ltspice/'
        lt = ltparser.LTspice()
        lt.read(path +"passive-filter-low-pass-omega.asc")
        lt.parse()

if __name__ == '__main__':
    unittest.main()
