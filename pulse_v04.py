#!/usr/bin/env python3
"""ATOCIA Pulse 0.4 — portable, read-only Linux laptop telemetry.

Reads (where permitted): MSR/MMIO RAPL energy counters, PSys, thermal zones,
CPU utilization/frequencies, AC/battery state, hwmon fan RPM and ACPI cooling
states. No CPU workload is started and no hardware setting is changed.
"""
from __future__ import annotations
import argparse
import csv
import glob
import os
import subprocess
import time
from datetime import datetime, timezone

import gpu_telemetry

MSR_ROOT = "/sys/devices/virtual/powercap/intel-rapl"
MMIO_ROOT = "/sys/devices/virtual/powercap/intel-rapl-mmio"

def txt(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""

def num(path: str):
    try:
        return int(txt(path))
    except (TypeError, ValueError):
        return None

def counter_delta_uj(current: int, previous: int, maximum: int):
    """Return a one-wrap energy delta in microjoules, or None if invalid."""
    if current is None or previous is None or maximum is None or maximum <= 0:
        return None
    if current < 0 or previous < 0 or current >= maximum or previous >= maximum:
        return None
    delta = current - previous
    if delta < 0:
        delta += maximum
    return delta if delta >= 0 else None

def energy_delta_to_watts(delta_uj, elapsed_s: float):
    """Convert a delta in microjoules over seconds into average watts."""
    if delta_uj is None or elapsed_s is None or elapsed_s <= 0:
        return None
    return round(delta_uj / 1_000_000 / elapsed_s, 4)

def discover_domains():
    """Find RAPL domains by their sysfs name, not by a fixed numeric index."""
    result = {}
    for root, interface in ((MSR_ROOT, "msr"), (MMIO_ROOT, "mmio")):
        for path in sorted(glob.glob(root + "/intel-rapl*")):
            if not os.path.isdir(path) or not os.path.isfile(path + "/energy_uj"):
                continue
            name = txt(path + "/name")
            if name == "package-0":
                key = interface + "_package"
            elif name == "psys" and interface == "msr":
                key = "psys"
            else:
                continue
            maximum = num(path + "/max_energy_range_uj")
            energy_path = path + "/energy_uj"
            # Skip protected counters in unprivileged mode; other telemetry
            # remains available and the caller emits a clear warning.
            if maximum and maximum > 0 and num(energy_path) is not None:
                result[key] = (energy_path, maximum)
    return result

def discover_zones():
    result = {}
    for root in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
        zone_type = txt(root + "/type").replace(",", "_").replace(" ", "_")
        if zone_type and os.path.isfile(root + "/temp"):
            result[os.path.basename(root) + "_" + zone_type] = root + "/temp"
    return result

def discover_hwmon_fans():
    result = {}
    for root in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        chip = txt(root + "/name") or os.path.basename(root)
        for path in sorted(glob.glob(root + "/fan*_input")):
            result[chip + "_" + os.path.basename(path)] = path
    return result

def discover_fan_cooling_states():
    result = {}
    for root in sorted(glob.glob("/sys/class/thermal/cooling_device*")):
        if txt(root + "/type").lower() == "fan":
            key = os.path.basename(root)
            result[key] = {
                "state": root + "/cur_state",
                "max_state": num(root + "/max_state"),
            }
    return result

def cpu_stats():
    result = {}
    try:
        with open("/proc/stat", "r", encoding="ascii") as f:
            for line in f:
                parts = line.split()
                if not parts:
                    continue
                label = parts[0]
                if label != "cpu" and not (label.startswith("cpu") and label[3:].isdigit()):
                    continue
                values = [int(x) for x in parts[1:]]
                if len(values) < 4:
                    continue
                idle = values[3] + (values[4] if len(values) > 4 else 0)
                result[label] = (sum(values), idle)
    except (OSError, ValueError):
        pass
    return result

def cpu_util_percent(before, after, key):
    if key not in before or key not in after:
        return ""
    total = after[key][0] - before[key][0]
    idle = after[key][1] - before[key][1]
    if total <= 0:
        return ""
    busy = min(max(total - idle, 0), total)
    return round(100 * busy / total, 2)

def cpu_policies():
    result = {}
    for root in sorted(glob.glob("/sys/devices/system/cpu/cpufreq/policy*")):
        key = os.path.basename(root)
        result[key] = {
            "frequency": root + "/scaling_cur_freq",
            "governor": txt(root + "/scaling_governor"),
            "epp": txt(root + "/energy_performance_preference"),
            "cpus": txt(root + "/related_cpus"),
        }
    return result

def get_power_profile():
    try:
        completed = subprocess.run(
            ["powerprofilesctl", "get"], capture_output=True,
            text=True, timeout=2, check=False
        )
        return completed.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument(
        "--output",
        default=os.path.expanduser("~/ATOCIA/pulse_v04.csv"),
    )
    args = parser.parse_args()
    if args.duration <= 0 or args.interval <= 0:
        parser.error("duration and interval must be positive")

    domains = discover_domains()
    zones = discover_zones()
    hwmon_fans = discover_hwmon_fans()
    fan_cooling = discover_fan_cooling_states()
    policies = cpu_policies()
    profile = get_power_profile()
    gpus = gpu_telemetry.discover_intel_gpus()
    previous_gpu_snapshot = gpu_telemetry.read_gpu_snapshot(gpus)
    previous_gpu_rc6 = {
        key: int(previous_gpu_snapshot.get("gpu_" + key + "_gt_rc6_residency_ms") or 0)
        for key in gpus
    }

    supplies = sorted(glob.glob("/sys/class/power_supply/*"))
    ac = next((p for p in supplies if txt(p + "/type") == "Mains"), None)
    battery = next((p for p in supplies if txt(p + "/type") == "Battery"), None)

    previous_energy = {key: num(path) for key, (path, _maximum) in domains.items()}
    previous_time = time.monotonic()
    start_time = previous_time
    previous_cpu = cpu_stats()

    fields = [
        "timestamp_utc", "elapsed_s", "power_profile",
        "ac_online", "battery_status", "battery_capacity_pct",
        "cpu_util_pct",
    ]
    cpu_names = sorted(k for k in previous_cpu if k != "cpu")
    fields += [name + "_util_pct" for name in cpu_names]
    fields += [name + "_freq_khz" for name in policies]
    for key in domains:
        fields += [key + "_energy_uj", key + "_power_w"]
    fields += ["temp_C_" + key for key in zones]
    fields += ["fan_rpm_" + key for key in hwmon_fans]
    fields += ["fan_state_" + key for key in fan_cooling]
    fields += gpu_telemetry.gpu_fields(gpus)

    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)
    count = 0

    with open(args.output, "w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        while time.monotonic() - start_time < args.duration:
            target = previous_time + args.interval
            time.sleep(max(0, target - time.monotonic()))
            now = time.monotonic()
            elapsed = now - previous_time
            current_cpu = cpu_stats()

            row = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "elapsed_s": round(now - start_time, 3),
                "power_profile": profile,
                "ac_online": txt(ac + "/online") if ac else "",
                "battery_status": txt(battery + "/status") if battery else "",
                "battery_capacity_pct": num(battery + "/capacity") if battery else "",
                "cpu_util_pct": cpu_util_percent(previous_cpu, current_cpu, "cpu"),
            }

            gpu_row = gpu_telemetry.read_gpu_snapshot(gpus, previous_gpu_rc6, elapsed)
            row.update(gpu_row)
            for key in gpus:
                value = gpu_row.get("gpu_" + key + "_gt_rc6_residency_ms", "")
                try:
                    previous_gpu_rc6[key] = int(value)
                except (TypeError, ValueError):
                    pass

            for name in cpu_names:
                row[name + "_util_pct"] = cpu_util_percent(previous_cpu, current_cpu, name)

            for policy, info in policies.items():
                row[policy + "_freq_khz"] = num(info["frequency"]) or ""

            for key, (path, maximum) in domains.items():
                current = num(path)
                row[key + "_energy_uj"] = current if current is not None else ""
                delta = counter_delta_uj(current, previous_energy.get(key), maximum)
                watts = energy_delta_to_watts(delta, elapsed)
                row[key + "_power_w"] = watts if watts is not None else ""
                previous_energy[key] = current

            for key, path in zones.items():
                value = num(path)
                row["temp_C_" + key] = round(value / 1000, 2) if value is not None else ""

            for key, path in hwmon_fans.items():
                value = num(path)
                row["fan_rpm_" + key] = value if value is not None else ""

            for key, info in fan_cooling.items():
                value = num(info["state"])
                row["fan_state_" + key] = value if value is not None else ""

            writer.writerow(row)
            output.flush()
            count += 1
            previous_time = now
            previous_cpu = current_cpu

            if count == 1:
                print(
                    "Detected: domains=%s thermal_zones=%d hwmon_fans=%d ACPI_fan_states=%d CPU_policies=%d"
                    % (sorted(domains), len(zones), len(hwmon_fans), len(fan_cooling), len(policies)),
                    flush=True,
                )
            msr_value = row.get("msr_package_power_w")
            mmio_value = row.get("mmio_package_power_w")
            msr_display = f"{msr_value:.2f} W" if isinstance(msr_value, (int, float)) else "unavailable"
            mmio_display = f"{mmio_value:.2f} W" if isinstance(mmio_value, (int, float)) else "unavailable"
            print(
                "sample=%d t=%.1fs CPU=%s%% MSR=%s MMIO=%s cooling=%s"
                % (
                    count, now - start_time, row["cpu_util_pct"],
                    msr_display, mmio_display,
                    {key: row["fan_state_" + key] for key in fan_cooling},
                ),
                flush=True,
            )

    if not any(key.endswith("_package") for key in domains):
        print(
            "WARNING: no readable RAPL package energy counter found; thermal/CPU telemetry was still collected.",
            flush=True,
        )
    print("DONE samples=%d output=%s" % (count, args.output), flush=True)
    print("NOTE: MSR and MMIO package counters are alternative views; never sum them.", flush=True)
    print("NOTE: PSys is a separate platform domain; do not add it to package power.", flush=True)
    if gpus:
        print("NOTE: GT non-RC6 residency is an activity proxy, not utilization; GPU power/temperature remain blank unless directly exposed.", flush=True)
    else:
        print("NOTE: no Intel DRM GT telemetry interface was discovered.", flush=True)

if __name__ == "__main__":
    main()
