"""Regression tests: python -m unittest discover -s unit_converter/tests -v"""
import importlib.util
import math
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "engineering_unit_converter.py"
spec = importlib.util.spec_from_file_location("engineering_unit_converter", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestEngineeringUnits(unittest.TestCase):
    def test_catalog(self):
        self.assertEqual(len(mod.UNIT_SETS), 25)
        self.assertEqual(sum(map(len, mod.UNIT_SETS.values())), 132)

    def test_known_values(self):
        cases = [
            (29, "압력 · Pressure (absolute)", "psi (psia)", "kPa", 199.947961501872),
            (10000, "힘/추력 · Force/Thrust", "lbf", "kN", 44.482216152605),
            (100, "질량유량 · Mass flow", "lbm/s", "kg/s", 45.359237),
            (1000, "온도 · Temperature", "°F", "°C", 537.7777777777778),
            (0.8, "TSFC · Thrust-specific fuel consumption",
             "lbm/(lbf·h)", "kg/(kN·h)", 81.57729703823428),
        ]
        for x, category, a, b, expected in cases:
            with self.subTest(category=category):
                self.assertAlmostEqual(mod.convert(x, category, a, b), expected, places=6)

    def test_roundtrips(self):
        for category, units in mod.UNIT_SETS.items():
            for a in units:
                for b in units:
                    for x in (1, 20, 1000):
                        with self.subTest(category=category, a=a, b=b, x=x):
                            result = mod.convert(x, category, a, b)
                            actual = mod.convert(result, category, b, a)
                            self.assertTrue(math.isclose(actual, x, rel_tol=1e-10, abs_tol=1e-9))

    def test_absolute_zero(self):
        with self.assertRaises(ValueError):
            mod.convert(-274, "온도 · Temperature", "°C", "K")

    def test_nonfinite(self):
        with self.assertRaises(ValueError):
            mod.convert(float("nan"), "압력 · Pressure (absolute)", "Pa", "kPa")

if __name__ == "__main__":
    unittest.main()
