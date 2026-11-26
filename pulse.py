#!/usr/bin/env python3
"""ATOCIA Pulse 0.1 — read-only Intel RAPL + thermal telemetry collector."""
import argparse, csv, glob, os, sys, time
from datetime import datetime, timezone

POWER_ROOT = "/sys/devices/virtual/powercap/intel-rapl"
THERMAL_ROOT = "/sys/class/thermal"

def read_int(path):
    with open(path, "r", encoding="ascii") as f:
        return int(f.read().strip())

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().strip()

def discover_domains():
    domains = {}
    for path in sorted(glob.glob(POWER_ROOT + "/intel-rapl:*")):
        if not os.path.isdir(path):
            continue
        try:
            name = read_text(path + "/name")
            if name in ("package-0", "psys") and os.path.isfile(path + "/energy_uj"):
                domains[name] = {"energy": path + "/energy_uj", "range": read_int(path + "/max_energy_range_uj")}
        except (OSError, ValueError):
            continue
    return domains

def discover_thermal():
    zones = []
    for path in sorted(glob.glob(THERMAL_ROOT + "/thermal_zone*")):
        try:
            label = read_text(path + "/type").strip().replace(",", "_")
            temp_path = path + "/temp"
            if os.path.isfile(temp_path):
                zones.append((os.path.basename(path) + "_" + label, temp_path))
        except OSError:
            continue
    return zones

def power_delta(previous, current, max_range, dt):
    delta = current - previous
    if delta < 0:
        delta += max_range
    if dt <= 0:
        return ""
    return delta / 1_000_000.0 / dt

def main():
    parser = argparse.ArgumentParser(description="Collect read-only RAPL and thermal data")
    parser.add_argument("--duration", type=float, default=60, help="seconds to collect (default: 60)")
    parser.add_argument("--interval", type=float, default=1.0, help="sample interval in seconds (default: 1)")
    parser.add_argument("--output", default="/home/iknowyou/ATOCIA/pulse.csv", help="CSV output path")
    args = parser.parse_args()
    if args.duration <= 0 or args.interval <= 0:
        parser.error("duration and interval must be positive")

    domains = discover_domains()
    if "package-0" not in domains:
        sys.exit("ERROR: RAPL package-0 energy counter unavailable")
    zones = discover_thermal()
    keys = list(domains.keys())
    previous = {key: read_int(domains[key]["energy"]) for key in keys}
    previous_t = time.monotonic()
    start_t = previous_t

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    fields = ["timestamp_utc", "elapsed_s"]
    for key in keys:
        fields += [key + "_energy_uj", key + "_power_w"]
    fields += ["temp_C_" + label for label, _ in zones]

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        count = 0
        while time.monotonic() - start_t < args.duration:
            target = previous_t + args.interval
            delay = target - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            now = time.monotonic()
            dt = now - previous_t
            row = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "elapsed_s": round(now - start_t, 4),
            }
            for key in keys:
                current = read_int(domains[key]["energy"])
                row[key + "_energy_uj"] = current
                row[key + "_power_w"] = round(power_delta(previous[key], current, domains[key]["range"], dt), 4)
                previous[key] = current
            for label, path in zones:
                try:
                    row["temp_C_" + label] = round(read_int(path) / 1000.0, 2)
                except (OSError, ValueError):
                    row["temp_C_" + label] = ""
            writer.writerow(row)
            f.flush()
            count += 1
            previous_t = now
            print("sample=%d elapsed=%.1fs " % (count, now - start_t) + " ".join(key + "=%.2fW" % row[key + "_power_w"] for key in keys), flush=True)
    print("DONE: %d samples written to %s" % (count, args.output))

if __name__ == "__main__":
    main()
