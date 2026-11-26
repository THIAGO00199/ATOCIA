#!/usr/bin/env python3
"""ATOCIA Pulse 0.3 — read-only laptop power, thermal and cooling telemetry.

Logs MSR and MMIO RAPL package interfaces separately; never adds their
energy counters. PSys is also kept separate. Reads fan cooling states without
commanding them. No stress workload is started and no settings are changed.
"""
from __future__ import annotations
import argparse
import csv
import glob
import os
import time
from datetime import datetime, timezone
import subprocess

RAPL_SOURCES = {
    "msr_package": "/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0",
    "mmio_package": "/sys/devices/virtual/powercap/intel-rapl-mmio/intel-rapl-mmio:0",
    "psys": "/sys/devices/virtual/powercap/intel-rapl/intel-rapl:1",
}

def txt(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""

def num(path: str):
    try:
        return int(txt(path))
    except (TypeError, ValueError):
        return None

def discover_domains():
    result = {}
    for key, root in RAPL_SOURCES.items():
        energy_path = root + "/energy_uj"
        if os.path.isfile(energy_path):
            maximum = num(root + "/max_energy_range_uj")
            if maximum:
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
                "device": os.path.realpath(root + "/device"),
            }
    return result

def cpu_stats():
    result = {}
    try:
        with open("/proc/stat", encoding="ascii") as f:
            for line in f:
                parts = line.split()
                if not parts or not (parts[0] == "cpu" or
                                     (parts[0].startswith("cpu") and parts[0][3:].isdigit())):
                    continue
                values = [int(x) for x in parts[1:]]
                idle = values[3] + (values[4] if len(values) > 4 else 0)
                result[parts[0]] = (sum(values), idle)
    except (OSError, ValueError):
        pass
    return result

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

def cpu_util_percent(before, after, key):
    if key not in before or key not in after:
        return ""
    total = after[key][0] - before[key][0]
    idle = after[key][1] - before[key][1]
    return round(100 * (total - idle) / total, 2) if total > 0 else ""

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--output", default="/home/iknowyou/ATOCIA/pulse_v03.csv")
    args = parser.parse_args()
    if args.duration <= 0 or args.interval <= 0:
        parser.error("duration and interval must be positive")

    domains = discover_domains()
    zones = discover_zones()
    hwmon_fans = discover_hwmon_fans()
    fan_cooling = discover_fan_cooling_states()
    policies = cpu_policies()
    if "msr_package" not in domains and "mmio_package" not in domains:
        raise SystemExit("No RAPL package energy counter found")

    supplies = sorted(glob.glob("/sys/class/power_supply/*"))
    ac = next((p for p in supplies if txt(p + "/type") == "Mains"), None)
    battery = next((p for p in supplies if txt(p + "/type") == "Battery"), None)
    try:
        profile = subprocess.run(
            ["powerprofilesctl", "get"], capture_output=True, text=True,
            timeout=2, check=False
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        profile = ""

    previous_energy = {key: num(path) for key, (path, _maximum) in domains.items()}
    previous_time = time.monotonic()
    start_time = previous_time
    previous_cpu = cpu_stats()

    fields = [
        "timestamp_utc", "elapsed_s", "power_profile",
        "ac_online", "battery_status", "battery_capacity_pct",
        "cpu_util_pct",
    ]
    cpu_names = sorted([k for k in previous_cpu if k.startswith("cpu") and k != "cpu"])
    fields += [name + "_util_pct" for name in cpu_names]
    fields += [name + "_freq_khz" for name in policies]
    for key in domains:
        fields += [key + "_energy_uj", key + "_power_w"]
    fields += ["temp_C_" + key for key in zones]
    fields += ["fan_rpm_" + key for key in hwmon_fans]
    fields += ["fan_state_" + key for key in fan_cooling]

    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)
    sample_count = 0

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        while time.monotonic() - start_time < args.duration:
            target = previous_time + args.interval
            time.sleep(max(0, target - time.monotonic()))
            now = time.monotonic()
            dt = now - previous_time
            current_cpu = cpu_stats()

            total_util = cpu_util_percent(previous_cpu, current_cpu, "cpu")
            row = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "elapsed_s": round(now - start_time, 3),
                "power_profile": profile,
                "ac_online": txt(ac + "/online") if ac else "",
                "battery_status": txt(battery + "/status") if battery else "",
                "battery_capacity_pct": num(battery + "/capacity") if battery else "",
                "cpu_util_pct": total_util,
            }
            for name in cpu_names:
                row[name + "_util_pct"] = cpu_util_percent(previous_cpu, current_cpu, name)

            for policy, info in policies.items():
                row[policy + "_freq_khz"] = num(info["frequency"]) or ""

            for key, (path, maximum) in domains.items():
                current = num(path)
                if current is None:
                    continue
                previous = previous_energy.get(key)
                row[key + "_energy_uj"] = current
                if previous is not None and dt > 0:
                    delta = current - previous
                    if delta < 0:
                        delta += maximum
                    row[key + "_power_w"] = round(delta / 1_000_000 / dt, 4)
                else:
                    row[key + "_power_w"] = ""
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
            f.flush()
            sample_count += 1
            previous_time = now
            previous_cpu = current_cpu
            print(
                "sample=%d t=%.1fs util=%s%% MSR=%sW MMIO=%sW fans=%s"
                % (
                    sample_count, now - start_time, total_util,
                    row.get("msr_package_power_w", "n/a"),
                    row.get("mmio_package_power_w", "n/a"),
                    {k: row["fan_state_" + k] for k in fan_cooling},
                ),
                flush=True,
            )

    print(
        "DONE samples=%d output=%s"
        % (sample_count, args.output),
        flush=True,
    )
    print("NOTE: MSR and MMIO package measurements are separate views; do not sum them.")
    print("NOTE: PSys is a separate platform-level domain; do not add it to package power.")

if __name__ == "__main__":
    main()
