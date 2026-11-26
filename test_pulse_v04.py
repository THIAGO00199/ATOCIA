#!/usr/bin/env python3
"""Offline unit tests for ATOCIA Pulse 0.4 helpers."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = str(Path(__file__).with_name("pulse_v04.py"))
SPEC = importlib.util.spec_from_file_location("pulse_v04", MODULE_PATH)
pulse = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pulse)

class TestEnergyMath(unittest.TestCase):
    def test_normal_counter_delta(self):
        self.assertEqual(pulse.counter_delta_uj(140, 100, 1000), 40)

    def test_single_counter_wrap(self):
        self.assertEqual(pulse.counter_delta_uj(5, 95, 100), 10)

    def test_invalid_counter_range_rejected(self):
        self.assertIsNone(pulse.counter_delta_uj(100, 95, 100))

    def test_invalid_maximum_rejected(self):
        self.assertIsNone(pulse.counter_delta_uj(10, 5, 0))

    def test_watts_conversion(self):
        self.assertEqual(pulse.energy_delta_to_watts(1_000_000, 2), 0.5)

    def test_bad_elapsed_time_rejected(self):
        self.assertIsNone(pulse.energy_delta_to_watts(1_000_000, 0))

    def test_missing_delta_rejected(self):
        self.assertIsNone(pulse.energy_delta_to_watts(None, 1))

class TestCpuMath(unittest.TestCase):
    def test_aggregate_utilization(self):
        before = {"cpu": (100, 20)}
        after = {"cpu": (200, 70)}
        self.assertEqual(pulse.cpu_util_percent(before, after, "cpu"), 50.0)

    def test_per_core_utilization(self):
        before = {"cpu0": (100, 40)}
        after = {"cpu0": (150, 65)}
        self.assertEqual(pulse.cpu_util_percent(before, after, "cpu0"), 50.0)

    def test_missing_cpu_returns_blank(self):
        self.assertEqual(pulse.cpu_util_percent({}, {}, "cpu"), "")

    def test_zero_interval_returns_blank(self):
        self.assertEqual(pulse.cpu_util_percent({"cpu": (1, 1)}, {"cpu": (1, 1)}, "cpu"), "")

class TestDomainDiscovery(unittest.TestCase):
    def make_domain(self, root, name, energy="1", maximum="1000"):
        os.makedirs(root, exist_ok=True)
        with open(os.path.join(root, "name"), "w", encoding="utf-8") as f:
            f.write(name)
        with open(os.path.join(root, "energy_uj"), "w", encoding="utf-8") as f:
            f.write(energy)
        with open(os.path.join(root, "max_energy_range_uj"), "w", encoding="utf-8") as f:
            f.write(maximum)

    def test_discovers_domains_by_name_not_numeric_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            msr = os.path.join(tmp, "intel-rapl")
            mmio = os.path.join(tmp, "intel-rapl-mmio")
            self.make_domain(os.path.join(msr, "intel-rapl:7"), "package-0")
            self.make_domain(os.path.join(msr, "intel-rapl:9"), "psys")
            self.make_domain(os.path.join(mmio, "intel-rapl-mmio:4"), "package-0")
            pulse.MSR_ROOT = msr
            pulse.MMIO_ROOT = mmio
            found = pulse.discover_domains()
            self.assertEqual(set(found), {"msr_package", "mmio_package", "psys"})
            self.assertTrue(found["msr_package"][0].endswith("intel-rapl:7/energy_uj"))
            self.assertTrue(found["mmio_package"][0].endswith("intel-rapl-mmio:4/energy_uj"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
