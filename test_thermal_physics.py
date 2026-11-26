#!/usr/bin/env python3
"""Offline tests for the exact lumped thermal RC baseline."""
import math
import unittest
from thermal_physics import SingleNodeRC, predict_constant_power


class TestSingleNodeRC(unittest.TestCase):
    def setUp(self):
        self.model = SingleNodeRC(resistance_k_per_w=2.0, capacitance_j_per_k=10.0)

    def test_time_constant_is_rc(self):
        self.assertEqual(self.model.time_constant_s, 20.0)

    def test_step_matches_analytic_solution(self):
        got = self.model.step(20.0, 5.0, 20.0, 20.0)
        equilibrium = 30.0
        expected = equilibrium + (20.0 - equilibrium) * math.exp(-1.0)
        self.assertAlmostEqual(got, expected, places=12)

    def test_zero_power_relaxes_toward_ambient(self):
        got = self.model.step(60.0, 0.0, 20.0, 20.0)
        self.assertGreater(got, 20.0)
        self.assertLess(got, 60.0)

    def test_equilibrium_is_fixed_point(self):
        equilibrium = self.model.equilibrium_temperature_c(5.0, 20.0)
        self.assertAlmostEqual(self.model.step(equilibrium, 5.0, 20.0, 7.0), equilibrium)

    def test_long_step_approaches_equilibrium(self):
        got = self.model.step(20.0, 5.0, 20.0, 1000.0)
        self.assertAlmostEqual(got, 30.0, places=8)

    def test_constant_power_forecast_is_conditional_projection(self):
        got = predict_constant_power(self.model, 20.0, 5.0, 20.0, 20.0)
        self.assertAlmostEqual(got, 30.0 - 10.0 / math.e)

    def test_simulation_rejects_non_monotonic_time(self):
        with self.assertRaises(ValueError):
            self.model.simulate(20.0, [(0.0, 0.0, 20.0), (1.0, 1.0, 20.0), (1.0, 1.0, 20.0)])

    def test_invalid_physical_parameters_rejected(self):
        with self.assertRaises(ValueError):
            SingleNodeRC(0.0, 10.0)
        with self.assertRaises(ValueError):
            SingleNodeRC(1.0, -1.0)

    def test_invalid_step_rejected(self):
        with self.assertRaises(ValueError):
            self.model.step(20.0, 1.0, 20.0, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
