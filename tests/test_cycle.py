"""Physics and conservation regression tests (stdlib unittest)."""
import unittest
from dataclasses import replace

from cycle1.physics import Gas, Station, combustor, compressor
from cycle1.solver import CycleInputs, solve_design_point

class DesignPointTests(unittest.TestCase):
    def test_baseline_positive_and_station_order(self):
        r = solve_design_point(CycleInputs())
        self.assertGreater(r.thrust_n, 0)
        self.assertGreater(r.mdot_fuel, 0)
        self.assertGreater(r.stations["3"].pt, r.stations["13"].pt)
        self.assertGreater(r.stations["4"].tt, r.stations["3"].tt)
        self.assertLess(r.stations["5"].tt, r.stations["45"].tt)

    def test_conservation(self):
        r = solve_design_point(CycleInputs())
        self.assertAlmostEqual(r.mass_residual_kg_s, 0, delta=1e-10)
        self.assertAlmostEqual(r.hp_shaft_residual_w, 0, delta=1e-6)
        self.assertAlmostEqual(r.lp_shaft_residual_w, 0, delta=1e-6)
        self.assertAlmostEqual(r.combustor_energy_residual_w, 0, delta=1e-6)

    def test_scaling_massflow(self):
        a = solve_design_point(CycleInputs(mdot_air=30))
        b = solve_design_point(CycleInputs(mdot_air=60))
        self.assertAlmostEqual(b.thrust_n / a.thrust_n, 2.0, places=10)
        self.assertAlmostEqual(a.tsfc_kg_per_ns, b.tsfc_kg_per_ns, places=12)

    def test_no_bypass(self):
        r = solve_design_point(CycleInputs(bypass_ratio=0))
        self.assertEqual(r.mdot_bypass_air, 0)
        self.assertEqual(r.bypass_nozzle.gross_thrust, 0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            solve_design_point(CycleInputs(mdot_air=-1))
        with self.assertRaises(ValueError):
            compressor(Station(300, 100000), 0.9, 0.85, Gas())
        with self.assertRaises(ValueError):
            combustor(Station(700, 250000), 1500, 0.95, 0.99, 1000000, Gas())

    def test_low_combustor_temperature(self):
        with self.assertRaises(ValueError):
            solve_design_point(replace(CycleInputs(), combustor_exit_tt=200))

if __name__ == "__main__":
    unittest.main()
