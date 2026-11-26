import os
import tempfile
import unittest
from pathlib import Path
import gpu_telemetry as gpu

class TestGpuTelemetry(unittest.TestCase):
    def fixture(self, root):
        card = Path(root) / "card0"
        device = card / "device"
        gt = card / "gt" / "gt0"
        gt.mkdir(parents=True)
        device.mkdir(exist_ok=True)
        def put(path, value):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(value))
        put(device / "vendor", "0x8086")
        put(card / "gt_act_freq_mhz", "600")
        put(card / "gt_cur_freq_mhz", "600")
        put(card / "gt_min_freq_mhz", "100")
        put(card / "gt_max_freq_mhz", "1300")
        put(card / "gt_boost_freq_mhz", "1300")
        put(gt / "rc6_residency_ms", "2000")
        for name in ("status", "thermal", "prochot", "pl1", "pl2", "pl4"):
            put(gt / ("throttle_reason_" + name), "0")
        return card, gt

    def test_discovers_intel_card_with_gt(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.fixture(tmp)
            found = gpu.discover_intel_gpus(tmp)
            self.assertEqual(list(found), ["card0"])
            self.assertTrue(found["card0"]["gt_path"].endswith("gt0"))

    def test_ignores_non_intel_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            card, _ = self.fixture(tmp)
            (card / "device" / "vendor").write_text("0x10de")
            self.assertEqual(gpu.discover_intel_gpus(tmp), {})

    def test_rc6_delta_produces_residency_proxy(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.fixture(tmp)
            found = gpu.discover_intel_gpus(tmp)
            row = gpu.read_gpu_snapshot(found, {"card0": 1500}, 1.0)
            self.assertEqual(row["gpu_card0_gt_non_rc6_residency_pct"], 50.0)

    def test_first_sample_has_no_activity_proxy(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.fixture(tmp)
            found = gpu.discover_intel_gpus(tmp)
            row = gpu.read_gpu_snapshot(found, {}, 1.0)
            self.assertEqual(row["gpu_card0_gt_non_rc6_residency_pct"], "")

    def test_does_not_invent_gpu_power_or_temperature(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.fixture(tmp)
            found = gpu.discover_intel_gpus(tmp)
            row = gpu.read_gpu_snapshot(found)
            self.assertEqual(row["gpu_card0_power_w"], "")
            self.assertEqual(row["gpu_card0_temperature_c"], "")
            self.assertEqual(row["gpu_card0_utilization_pct"], "")

if __name__ == "__main__":
    unittest.main(verbosity=2)
