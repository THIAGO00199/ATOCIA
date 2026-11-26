#!/usr/bin/env python3
"""ATOCIA Powercap Audit — read-only comparison of Intel RAPL interfaces.

Reads sysfs and system identity only. Never writes power limits, governors,
profiles, thermal settings, firmware, or device state.
"""
from __future__ import annotations
import argparse
import glob
import os
import platform
import subprocess
from datetime import datetime, timezone

MSR_ROOT = "/sys/devices/virtual/powercap/intel-rapl"
MMIO_ROOT = "/sys/devices/virtual/powercap/intel-rapl-mmio"

def read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError as exc:
        return f"unavailable ({exc.__class__.__name__})"

def command(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=3, check=False)
        return (result.stdout or result.stderr).strip() or "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"

def read_interface(root: str) -> dict:
    result = {"path": root, "present": os.path.isdir(root)}
    if not result["present"]:
        return result
    result["name"] = read(root + "/name")
    result["energy_uj"] = read(root + "/energy_uj")
    result["max_energy_range_uj"] = read(root + "/max_energy_range_uj")
    result["constraints"] = []
    for idx in range(4):
        base = f"{root}/constraint_{idx}_"
        name = read(base + "name")
        if name.startswith("unavailable"):
            continue
        result["constraints"].append({
            "name": name,
            "limit_uw": read(base + "power_limit_uw"),
            "max_uw": read(base + "max_power_uw"),
            "window_us": read(base + "time_window_us"),
        })
    return result


def discover_interfaces() -> dict:
    """Find RAPL domains by sysfs name instead of fixed numeric indexes."""
    result = {}
    for path in sorted(glob.glob(MSR_ROOT + "/intel-rapl:*")):
        if not os.path.isdir(path):
            continue
        name = read(path + "/name")
        if name == "package-0":
            label = "MSR"
        elif name == "psys":
            label = "PSys"
        elif name.startswith("package-"):
            label = "MSR " + name
        else:
            continue
        result[label] = read_interface(path)

    for path in sorted(glob.glob(MMIO_ROOT + "/intel-rapl-mmio:*")):
        if not os.path.isdir(path):
            continue
        name = read(path + "/name")
        if name == "package-0":
            label = "MMIO"
        elif name.startswith("package-"):
            label = "MMIO " + name
        else:
            continue
        result[label] = read_interface(path)
    return result


def discover_pci_thermal() -> list:
    """Find Intel processor-thermal PCI devices without assuming bus address."""
    result = []
    for path in sorted(glob.glob("/sys/bus/pci/devices/*")):
        vendor = read(path + "/vendor")
        device = read(path + "/device")
        pci_class = read(path + "/class")
        driver_path = path + "/driver"
        driver = os.path.basename(os.path.realpath(driver_path)) if os.path.exists(driver_path) else "unbound"
        if vendor == "0x8086" and (driver == "proc_thermal" or pci_class.startswith("0x118")):
            result.append({
                "address": os.path.basename(path),
                "vendor": vendor,
                "device": device,
                "class": pci_class,
                "driver": driver,
            })
    return result

def as_number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def watts(value):
    n = as_number(value)
    return f"{n / 1_000_000:.2f} W" if n is not None else "n/a"

def seconds(value):
    n = as_number(value)
    return f"{n / 1_000_000:.3f} s" if n is not None else "n/a"

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=os.path.expanduser("~/ATOCIA/POWER_CAP_AUDIT_2026-11-20.md"))
    args = parser.parse_args()

    dmi = {
        "Manufacturer": read("/sys/class/dmi/id/sys_vendor"),
        "Model": read("/sys/class/dmi/id/product_name"),
        "Board": read("/sys/class/dmi/id/board_name"),
        "BIOS": read("/sys/class/dmi/id/bios_version"),
    }
    cpu_model = "unknown"
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.lower().startswith("model name"):
                    cpu_model = line.split(":", 1)[1].strip()
                    break
    except OSError:
        pass

    pci_devices = discover_pci_thermal()
    pci_id = ", ".join(
        f"{item['address']} {item['vendor']}:{item['device']}" for item in pci_devices
    ) if pci_devices else "not detected"
    pci_driver = ", ".join(item["driver"] for item in pci_devices) if pci_devices else "unavailable"
    profile = command(["powerprofilesctl", "get"])
    interfaces = discover_interfaces()

    policies = sorted(glob.glob("/sys/devices/system/cpu/cpufreq/policy*"))
    policy_rows = []
    for path in policies:
        policy_rows.append({
            "policy": os.path.basename(path),
            "governor": read(path + "/scaling_governor"),
            "epp": read(path + "/energy_performance_preference"),
            "min_khz": read(path + "/scaling_min_freq"),
            "max_khz": read(path + "/scaling_max_freq"),
            "related_cpus": read(path + "/related_cpus"),
        })

    services = {svc: command(["systemctl", "is-active", svc]) for svc in
                ("power-profiles-daemon", "thermald", "tlp", "auto-cpufreq", "tuned")}

    lines = [
        "# ATOCIA — Powercap consistency audit",
        "",
        f"- Collected (UTC): {datetime.now(timezone.utc).isoformat()}",
        "- Mode: read-only; no hardware or system settings were changed.",
        "",
        "## Device",
        "",
    ]
    lines += [f"- {key}: {value}" for key, value in dmi.items()]
    lines += [
        f"- CPU: {cpu_model}",
        f"- Kernel: {platform.release()}",
        f"- Processor Thermal PCI ID: {pci_id}",
        f"- Processor Thermal driver: {pci_driver}",
        f"- Power profile: {profile}",
        "",
        "## CPU policies",
        "",
        "| Policy | CPUs | Governor | EPP | Min MHz | Max MHz |",
        "|---|---|---|---|---:|---:|",
    ]
    for row in policy_rows:
        min_mhz = f"{int(row['min_khz'])/1000:.0f}" if row["min_khz"].isdigit() else "n/a"
        max_mhz = f"{int(row['max_khz'])/1000:.0f}" if row["max_khz"].isdigit() else "n/a"
        lines.append(f"| {row['policy']} | {row['related_cpus']} | {row['governor']} | {row['epp']} | {min_mhz} | {max_mhz} |")

    lines += ["", "## RAPL interfaces", ""]
    for label, item in interfaces.items():
        lines += [f"### {label}", ""]
        if not item["present"]:
            lines.append("Interface not present.")
            lines.append("")
            continue
        lines += [
            f"- Name: {item.get('name', 'n/a')}",
            f"- Energy counter: {item.get('energy_uj', 'n/a')} µJ",
            f"- Counter wrap range: {item.get('max_energy_range_uj', 'n/a')} µJ",
            "",
            "| Constraint | Configured limit | Reference value | Window | Comparison |",
            "|---|---:|---:|---:|---|",
        ]
        for c in item["constraints"]:
            lim = watts(c["limit_uw"])
            mx = watts(c["max_uw"])
            win = seconds(c["window_us"])
            limit_n, max_n = as_number(c["limit_uw"]), as_number(c["max_uw"])
            status = "not comparable"
            if limit_n is not None and max_n is not None and max_n > 0:
                if c["name"] == "long_term":
                    status = "above thermal-spec reference" if limit_n > max_n else "at/below thermal-spec reference"
                else:
                    status = "at/below reported reference" if limit_n <= max_n else "above reported reference"
            lines.append(f"| {c['name']} | {lim} | {mx} | {win} | {status} |")
        lines.append("")

    msr_energy = as_number(interfaces.get("MSR", {}).get("energy_uj"))
    mmio_energy = as_number(interfaces.get("MMIO", {}).get("energy_uj"))
    if msr_energy is not None and mmio_energy is not None:
        diff = abs(msr_energy - mmio_energy)
        relative = diff / max(msr_energy, mmio_energy, 1) * 100
        lines += [
            "## Cross-interface comparison",
            "",
            f"- Absolute energy-counter difference at read time: {diff} µJ ({relative:.8f}% of the counter magnitude).",
            "- The counters are two views of the package domain. Do not add them together.",
            "- A tiny difference can result from the sequential reads occurring at slightly different instants.",
            "",
        ]

    lines += [
        "## Power-management services",
        "",
        "| Service | State |",
        "|---|---|",
    ]
    for svc, state in services.items():
        lines.append(f"| {svc} | {state} |")

    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- A power limit is a configured constraint, not the instantaneous power draw.",
        "- MSR and MMIO are separate access interfaces; their limits must be recorded separately.",
        "- A difference between interfaces is a diagnostic observation, not automatically a defect.",
        "- For the RAPL PL1/long_term constraint, the Linux driver currently maps max_power_uw to THERMAL_SPEC_POWER. Treat it as a thermal-spec/TDP reference, not automatically as a hard register ceiling.",
        "- A configured PL1 above that reference is recorded for review, not automatically classified as a defect.",
        "- Package energy counters are alternative views of the package domain and must not be summed.",
        "- This audit does not estimate savings, benchmark performance, or assert which limit is effective.",
        "",
        "## Technical references",
        "",
        "- Linux kernel Tiger Lake processor-thermal PCI support and MMIO RAPL registration: https://lkml.iu.edu/hypermail/linux/kernel/2011.3/03463.html",
        "- Linux processor thermal MMIO RAPL implementation: https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/1334d2a3b3235d062e5e1f51aebe7a64ed57cf72/drivers/thermal/intel/int340x_thermal/processor_thermal_rapl.c",
        "- Linux powercap sysfs interface: https://www.kernel.org/doc/html/latest/power/powercap/powercap.html",
        "- Linux RAPL common code maps PL1 max-power reporting to THERMAL_SPEC_POWER: https://github.com/torvalds/linux/blob/master/drivers/powercap/intel_rapl_common.c",
        "- Intel Core i7-1165G7 product specifications (cTDP-down 12 W, cTDP-up 28 W): https://www.intel.com/content/www/us/en/products/sku/208662/intel-core-i71165g7-processor-12m-cache-up-to-4-70-ghz/specifications.html",
        "",
    ]

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"\nWROTE: {args.output}")

if __name__ == "__main__":
    main()
