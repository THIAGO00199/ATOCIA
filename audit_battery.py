#!/usr/bin/env python3
"""ATOCIA Battery Audit — read-only battery and charging report."""
from __future__ import annotations
import argparse
import glob
import os
from datetime import datetime, timezone

ROOT = "/sys/class/power_supply"

def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""

def number(path):
    try:
        return float(read(path))
    except (TypeError, ValueError):
        return None


def capacity_retention_percent(charge_full, charge_full_design):
    """Estimate retained full-charge capacity relative to design capacity."""
    if charge_full is None or charge_full_design is None or charge_full_design <= 0:
        return None
    if charge_full < 0:
        return None
    return 100.0 * charge_full / charge_full_design

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=os.path.expanduser("~/ATOCIA/BATTERY_AUDIT_2026-11-20.md"),
    )
    args = parser.parse_args()
    supplies = sorted(glob.glob(ROOT + "/*"))
    mains = next((p for p in supplies if read(p + "/type") == "Mains"), None)
    batteries = [
        p for p in supplies
        if read(p + "/type") == "Battery"
        and any(os.path.isfile(p + "/" + field) for field in (
            "capacity", "charge_full", "charge_full_design",
            "energy_full", "energy_full_design",
        ))
        and read(p + "/present") != "0"
    ]

    lines = [
        "# ATOCIA — Battery and charging audit",
        "",
        f"- Collected (UTC): {datetime.now(timezone.utc).isoformat()}",
        "- Mode: read-only; no charge thresholds or power settings were changed.",
        "",
        "## AC adapter",
        "",
        f"- Online: {read(mains + '/online') if mains else 'not detected'}",
        "",
    ]

    if not batteries:
        lines += ["## Battery", "", "No battery power-supply device was detected.", ""]
    else:
        for index, battery in enumerate(batteries, 1):
            name = os.path.basename(battery)
            status = read(battery + "/status") or "unknown"
            present = read(battery + "/present") or "unknown"
            soc = number(battery + "/capacity")
            charge_full = number(battery + "/charge_full")
            design = number(battery + "/charge_full_design")
            charge_now = number(battery + "/charge_now")
            cycles = read(battery + "/cycle_count") or "not exposed"
            voltage = number(battery + "/voltage_now")
            current = number(battery + "/current_now")
            end_threshold = read(battery + "/charge_control_end_threshold") or "not exposed"
            health = capacity_retention_percent(charge_full, design)

            lines += [
                f"## Battery {index} ({name})",
                "",
                f"- Present: {present}",
                f"- Status: {status}",
                f"- State of charge: {soc:.1f}%" if soc is not None else "- State of charge: not exposed",
                f"- Estimated full-capacity retention: {health:.1f}%" if health is not None else "- Estimated full-capacity retention: not available",
                f"- Charge cycles: {cycles}",
                f"- Current end-charge threshold: {end_threshold}%" if end_threshold.isdigit() else f"- Current end-charge threshold: {end_threshold}",
                f"- Voltage: {voltage / 1_000_000:.3f} V" if voltage is not None else "- Voltage: not exposed",
                f"- Current: {current / 1_000_000:.3f} A" if current is not None else "- Current: not exposed",
                f"- Current stored charge: {charge_now / 1_000_000:.3f} Ah" if charge_now is not None else "- Current stored charge: not exposed",
                f"- Full charge capacity: {charge_full / 1_000_000:.3f} Ah" if charge_full is not None else "- Full charge capacity: not exposed",
                f"- Design charge capacity: {design / 1_000_000:.3f} Ah" if design is not None else "- Design charge capacity: not exposed",
                "",
            ]

    lines += [
        "## Interpretation guardrails",
        "",
        "- Capacity retention is estimated from the battery controller's reported full-charge and design capacities. Calibration, temperature and battery age can affect it.",
        "- Cycle count and percentage alone do not diagnose a battery fault.",
        "- A charge threshold is recorded as reported; this audit does not change it or assume it explains the current charge state.",
        "- Current and voltage readings are instantaneous snapshots, not a stable whole-system power measurement.",
        "- Battery telemetry does not replace an external power meter when validating whole-system energy savings.",
        "- The report intentionally does not collect battery serial numbers or other unique device identifiers.",
        "",
    ]

    output = args.output
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print("\nWROTE:", output)

if __name__ == "__main__":
    main()
