#!/usr/bin/env python3
"""Offline tests for ATOCIA powercap and battery audit helpers."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent

def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

audit = load_module("audit_powercap", "audit_powercap.py")
battery = load_module("audit_battery", "audit_battery.py")

class TestPowercapHelpers(unittest.TestCase):
    def make_domain(self, root, name, limit="10000000", reference="28000000"):
        os.makedirs(root, exist_ok=True)
        values = {
            "name": name,
            "energy_uj": "123456",
            "max_energy_range_uj": "999999",
            "constraint_0_name": "long_term",
            "constraint_0_power_limit_uw": limit,
            "constraint_0_max_power_uw": reference,
            "constraint_0_time_window_us": "27983872",
        }
        for key, value in values.items():
            with open(os.path.join(root, key), "w", encoding="utf-8") as f:
                f.write(value)

    def test_discovery_finds_domains_by_name_not_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            msr = os.path.join(tmp, "intel-rapl")
            mmio = os.path.join(tmp, "intel-rapl-mmio")
            self.make_domain(os.path.join(msr, "intel-rapl:7"), "package-0")
            self.make_domain(os.path.join(msr, "intel-rapl:9"), "psys", limit="57000000", reference="0")
            self.make_domain(os.path.join(mmio, "intel-rapl-mmio:4"), "package-0")
            old_msr, old_mmio = audit.MSR_ROOT, audit.MMIO_ROOT
            try:
                audit.MSR_ROOT, audit.MMIO_ROOT = msr, mmio
                found = audit.discover_interfaces()
            finally:
                audit.MSR_ROOT, audit.MMIO_ROOT = old_msr, old_mmio
            self.assertEqual(set(found), {"MSR", "PSys", "MMIO"})
            self.assertEqual(found["MSR"]["name"], "package-0")
            self.assertEqual(found["PSys"]["name"], "psys")
            self.assertEqual(found["MMIO"]["name"], "package-0")
            self.assertEqual(found["MSR"]["constraints"][0]["limit_uw"], "10000000")

    def test_watts_format(self):
        self.assertEqual(audit.watts("12500000"), "12.50 W")
        self.assertEqual(audit.watts("not-a-number"), "n/a")

    def test_reference_comparison_is_not_encoded_as_fault(self):
        # The raw values remain available; the product report carries the
        # thermal-spec caveat instead of declaring an automatic defect.
        self.assertEqual(audit.as_number("40000000"), 40000000)
        self.assertEqual(audit.as_number("28000000"), 28000000)

class TestBatteryHelpers(unittest.TestCase):
    def test_capacity_retention(self):
        self.assertAlmostEqual(battery.capacity_retention_percent(3.19, 3.78), 84.3915, places=3)

    def test_missing_or_zero_design_capacity(self):
        self.assertIsNone(battery.capacity_retention_percent(3.0, None))
        self.assertIsNone(battery.capacity_retention_percent(3.0, 0))

    def test_negative_full_capacity_is_rejected(self):
        self.assertIsNone(battery.capacity_retention_percent(-1, 3.78))

if __name__ == "__main__":
    unittest.main(verbosity=2)
