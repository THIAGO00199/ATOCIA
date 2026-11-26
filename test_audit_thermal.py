#!/usr/bin/env python3
"""Offline tests for ATOCIA thermal-audit review rules."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("audit_thermal", ROOT / "audit_thermal.py")
thermal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(thermal)

class TestThermalReviewRules(unittest.TestCase):
    def test_active_trip_reached_with_fan_state_zero_flags_review(self):
        self.assertTrue(thermal.fan_state_requires_review(51000, 50000, "active", 0, "Fan"))

    def test_temperature_below_trip_does_not_flag(self):
        self.assertFalse(thermal.fan_state_requires_review(49000, 50000, "active", 0, "Fan"))

    def test_passive_trip_does_not_flag(self):
        self.assertFalse(thermal.fan_state_requires_review(90000, 50000, "passive", 0, "Fan"))

    def test_fan_state_nonzero_does_not_flag(self):
        self.assertFalse(thermal.fan_state_requires_review(51000, 50000, "active", 1, "Fan"))

    def test_non_fan_cooling_device_does_not_flag(self):
        self.assertFalse(thermal.fan_state_requires_review(51000, 50000, "active", 0, "Processor"))

    def test_missing_sensor_data_does_not_flag(self):
        self.assertFalse(thermal.fan_state_requires_review(None, 50000, "active", 0, "Fan"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
