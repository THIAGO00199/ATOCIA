#!/usr/bin/env python3
"""Read-only Intel DRM/i915 GT telemetry for ATOCIA.

Frequency and RC6 residency are hardware/driver telemetry. RC6-derived
non-residency is only an activity proxy, not GPU utilization. This module
never writes sysfs and never starts a workload.
"""
from __future__ import annotations
import glob
import os
import re

def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""

def _integer(path: str):
    value = _read(path)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def discover_intel_gpus(drm_root: str = "/sys/class/drm"):
    """Return Intel DRM cards exposing read-only GT frequency telemetry."""
    found = {}
    for card in sorted(glob.glob(os.path.join(drm_root, "card[0-9]*"))):
        if not re.fullmatch(r"card[0-9]+", os.path.basename(card)):
            continue
        device = os.path.join(card, "device")
        if _read(os.path.join(device, "vendor")).lower() != "0x8086":
            continue
        gt = os.path.join(card, "gt", "gt0")
        if not os.path.isdir(gt):
            continue
        driver_link = os.path.join(device, "driver")
        try:
            driver = os.path.basename(os.path.realpath(driver_link))
        except OSError:
            driver = ""
        name = _read(os.path.join(device, "uevent"))
        found[os.path.basename(card)] = {
            "card_path": card,
            "gt_path": gt,
            "driver": driver,
            "device_info": name.replace("\\n", "; "),
        }
    return found

def gpu_fields(devices):
    """Stable CSV field names for discovered Intel GT devices."""
    fields = []
    for key in devices:
        prefix = "gpu_" + key
        fields.extend([
            prefix + "_driver", prefix + "_gt_act_freq_mhz",
            prefix + "_gt_cur_freq_mhz", prefix + "_gt_min_freq_mhz",
            prefix + "_gt_max_freq_mhz", prefix + "_gt_boost_freq_mhz",
            prefix + "_gt_rc6_residency_ms",
            prefix + "_gt_non_rc6_residency_pct",
            prefix + "_throttle_reason_status",
            prefix + "_throttle_reason_thermal",
            prefix + "_throttle_reason_prochot",
            prefix + "_throttle_reason_pl1",
            prefix + "_throttle_reason_pl2",
            prefix + "_throttle_reason_pl4",
            prefix + "_temperature_c",
            prefix + "_power_w",
            prefix + "_utilization_pct",
        ])
    return fields

def read_gpu_snapshot(devices, previous_rc6=None, elapsed_s=None):
    """Read one snapshot; unavailable direct GPU power/temp/util remain blank."""
    previous_rc6 = previous_rc6 or {}
    row = {}
    for key, info in devices.items():
        prefix = "gpu_" + key
        card, gt = info["card_path"], info["gt_path"]
        row[prefix + "_driver"] = info["driver"]
        mapping = {
            "_gt_act_freq_mhz": os.path.join(card, "gt_act_freq_mhz"),
            "_gt_cur_freq_mhz": os.path.join(card, "gt_cur_freq_mhz"),
            "_gt_min_freq_mhz": os.path.join(card, "gt_min_freq_mhz"),
            "_gt_max_freq_mhz": os.path.join(card, "gt_max_freq_mhz"),
            "_gt_boost_freq_mhz": os.path.join(card, "gt_boost_freq_mhz"),
            "_gt_rc6_residency_ms": os.path.join(gt, "rc6_residency_ms"),
            "_throttle_reason_status": os.path.join(gt, "throttle_reason_status"),
            "_throttle_reason_thermal": os.path.join(gt, "throttle_reason_thermal"),
            "_throttle_reason_prochot": os.path.join(gt, "throttle_reason_prochot"),
            "_throttle_reason_pl1": os.path.join(gt, "throttle_reason_pl1"),
            "_throttle_reason_pl2": os.path.join(gt, "throttle_reason_pl2"),
            "_throttle_reason_pl4": os.path.join(gt, "throttle_reason_pl4"),
        }
        for suffix, path in mapping.items():
            value = _read(path)
            row[prefix + suffix] = value
        current = _integer(mapping["_gt_rc6_residency_ms"])
        previous = previous_rc6.get(key)
        proxy = ""
        if current is not None and previous is not None and elapsed_s and elapsed_s > 0:
            delta_ms = current - previous
            elapsed_ms = elapsed_s * 1000.0
            if 0 <= delta_ms <= elapsed_ms * 1.25:
                proxy = round(100.0 * max(0.0, min(1.0, 1.0 - delta_ms / elapsed_ms)), 2)
        row[prefix + "_gt_non_rc6_residency_pct"] = proxy
        # Intel i915 on this platform exposes no isolated GPU temperature or
        # power sensor through the discovered interface. Never substitute CPU
        # package temperature or package/PSys energy.
        row[prefix + "_temperature_c"] = ""
        row[prefix + "_power_w"] = ""
        row[prefix + "_utilization_pct"] = ""
    return row
