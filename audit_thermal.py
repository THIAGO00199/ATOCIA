#!/usr/bin/env python3
"""ATOCIA Thermal Audit — read-only thermal zones, trips and cooling topology."""
from __future__ import annotations
import argparse
import glob
import os
from datetime import datetime, timezone

def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""

def number(path):
    try:
        return int(read(path))
    except (TypeError, ValueError):
        return None


def format_temperature(temp_mC):
    """Format millidegrees Celsius; zero-Kelvin placeholders are not real trips."""
    if temp_mC is None:
        return "not exposed"
    if temp_mC <= -200000:
        return "not configured (zero-Kelvin sentinel)"
    return f"{temp_mC / 1000:.2f}°C"

def fan_state_requires_review(zone_temp_mC, trip_temp_mC, trip_type, fan_state, device_type):
    """Conservative review flag only; never infer a physical fan failure."""
    return (
        zone_temp_mC is not None
        and trip_temp_mC is not None
        and zone_temp_mC >= 0
        and trip_temp_mC >= 0
        and trip_type == "active"
        and device_type.lower() == "fan"
        and fan_state == 0
        and zone_temp_mC >= trip_temp_mC
    )

def discover_zones():
    zones = []
    review_flags = []
    for root in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
        zone_name = os.path.basename(root)
        zone_type = read(root + "/type") or "unknown"
        temp_mC = number(root + "/temp")
        trips = {}
        for trip_path in sorted(glob.glob(root + "/trip_point_*_temp")):
            filename = os.path.basename(trip_path)
            index = filename.removeprefix("trip_point_").removesuffix("_temp")
            trips[index] = {
                "type": read(root + f"/trip_point_{index}_type"),
                "temp_mC": number(trip_path),
            }

        cooling = []
        for link in sorted(glob.glob(root + "/cdev*")):
            if not os.path.islink(link):
                continue
            link_name = os.path.basename(link)
            target = os.path.realpath(link)
            device_type = read(target + "/type") or "unknown"
            trip_index = read(root + f"/{link_name}_trip_point")
            trip = trips.get(trip_index, {})
            state = number(target + "/cur_state")
            max_state = number(target + "/max_state")
            item = {
                "id": os.path.basename(target),
                "type": device_type,
                "trip_index": trip_index,
                "trip_type": trip.get("type", "unknown"),
                "trip_temp_mC": trip.get("temp_mC"),
                "state": state,
                "max_state": max_state,
                "device": os.path.realpath(target + "/device"),
            }
            cooling.append(item)
            if fan_state_requires_review(
                temp_mC, item["trip_temp_mC"], item["trip_type"],
                state, device_type
            ):
                review_flags.append(
                    f"{zone_name} ({zone_type}) reads {temp_mC/1000:.1f}°C "
                    f"at/above active trip {trip_index} "
                    f"({item['trip_temp_mC']/1000:.1f}°C), while "
                    f"{item['id']} reports state 0. Review sensor/firmware mapping; "
                    "this does not establish physical fan failure."
                )

        zones.append({
            "name": zone_name,
            "type": zone_type,
            "temp_mC": temp_mC,
            "policy": read(root + "/policy") or "not exposed",
            "mode": read(root + "/mode") or "not exposed",
            "trips": trips,
            "cooling": cooling,
        })
    return zones, review_flags

def discover_hwmon_fans():
    fans = []
    for root in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        chip = read(root + "/name") or os.path.basename(root)
        for path in sorted(glob.glob(root + "/fan*_input")):
            fans.append((chip, os.path.basename(path), read(path)))
    return fans

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=os.path.expanduser("~/ATOCIA/THERMAL_AUDIT_2026-11-20.md"),
    )
    args = parser.parse_args()
    zones, flags = discover_zones()
    hwmon_fans = discover_hwmon_fans()

    lines = [
        "# ATOCIA — Thermal and cooling audit",
        "",
        f"- Collected (UTC): {datetime.now(timezone.utc).isoformat()}",
        "- Mode: read-only; no thermal policy, fan state or firmware setting was changed.",
        "",
        "## Thermal zones and cooling devices",
        "",
    ]
    for zone in zones:
        temp = format_temperature(zone["temp_mC"])
        lines += [
            f"### {zone['name']} — {zone['type']}",
            "",
            f"- Temperature: {temp}",
            f"- Policy: {zone['policy']}",
            f"- Mode: {zone['mode']}",
            "",
        ]
        if zone["trips"]:
            lines += [
                "| Trip | Type | Temperature |",
                "|---:|---|---:|",
            ]
            for index, trip in sorted(zone["trips"].items(), key=lambda pair: int(pair[0])):
                value = format_temperature(trip["temp_mC"])
                lines.append(f"| {index} | {trip['type']} | {value} |")
            lines.append("")
        if zone["cooling"]:
            lines += [
                "| Cooling device | Type | Linked trip | Current state | Device path |",
                "|---|---|---|---:|---|",
            ]
            for item in zone["cooling"]:
                trip_temp = format_temperature(item["trip_temp_mC"])
                state = f"{item['state']}/{item['max_state']}" if item["state"] is not None else "not exposed"
                lines.append(
                    f"| {item['id']} | {item['type']} | "
                    f"{item['trip_index']} ({item['trip_type']}, {trip_temp}) | "
                    f"{state} | {item['device']} |"
                )
            lines.append("")

    lines += ["## hwmon fan tachometers", ""]
    if hwmon_fans:
        lines += ["| Chip | Input | RPM |", "|---|---|---:|"]
        for chip, input_name, value in hwmon_fans:
            lines.append(f"| {chip} | {input_name} | {value} |")
    else:
        lines.append("No fan RPM input was exposed through inspected hwmon interfaces.")
    lines += ["", "## Review-only observations", ""]
    if flags:
        lines.append("The following patterns merit technician review and are not fault verdicts:")
        lines += [f"- {flag}" for flag in flags]
    else:
        lines.append("No active-trip / fan-state mismatch was detected in this snapshot.")
    lines += [
        "",
        "## Interpretation limits",
        "",
        "- ACPI cooling-device states are not RPM readings and do not establish physical fan count or airflow.",
        "- A zone may not be the sensor used by the embedded controller for physical fan behavior.",
        "- Firmware may independently manage cooling; a state mismatch is not proof of a stopped fan or cooling fault.",
        "- The audit never writes cooling-device state, fan controls, thermal policies or firmware.",
        "",
    ]

    output = os.path.expanduser(args.output)
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"\nWROTE: {output}")

if __name__ == "__main__":
    main()
