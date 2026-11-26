#!/usr/bin/env python3
"""ATOCIA — local, read-only Linux laptop diagnostic runner.

All subcommands inspect telemetry or create local reports/CSV files.
No CPU stress workload is started and no hardware/system settings are changed.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def run_step(label: str, command: list[str]) -> int:
    print(f"\n=== {label} ===", flush=True)
    result = subprocess.run(command, check=False)
    if result.returncode:
        print(f"ATOCIA: {label} exited with status {result.returncode}", flush=True)
    return result.returncode

def self_test() -> int:
    return run_step(
        "Offline unit tests",
        [
            sys.executable, "-m", "unittest", "discover",
            "-s", str(ROOT), "-p", "test_*.py", "-v",
        ],
    )

def audit(report_dir: Path) -> int:
    report_dir.mkdir(parents=True, exist_ok=True)
    code = 0
    code |= run_step(
        "Power and CPU policy audit",
        [
            sys.executable, str(ROOT / "audit_powercap.py"),
            "--output", str(report_dir / "POWER_CAP_AUDIT_2026-11-20.md"),
        ],
    )
    code |= run_step(
        "Battery and charging audit",
        [
            sys.executable, str(ROOT / "audit_battery.py"),
            "--output", str(report_dir / "BATTERY_AUDIT_2026-11-20.md"),
        ],
    )
    code |= run_step(
        "Thermal zones and cooling-topology audit",
        [
            sys.executable, str(ROOT / "audit_thermal.py"),
            "--output", str(report_dir / "THERMAL_AUDIT_2026-11-20.md"),
        ],
    )
    return code

def capture(report_dir: Path, duration: float, interval: float, filename: str) -> int:
    report_dir.mkdir(parents=True, exist_ok=True)
    output = report_dir / filename
    return run_step(
        "Passive telemetry capture (no stress load)",
        [
            sys.executable, str(ROOT / "pulse_v04.py"),
            "--duration", str(duration),
            "--interval", str(interval),
            "--output", str(output),
        ],
    )

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-dir",
        default=os.path.expanduser("~/ATOCIA"),
        help="directory for reports and CSV captures (default: ~/ATOCIA)",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("selftest", help="run offline mathematical and discovery tests")
    sub.add_parser("audit", help="create read-only power, CPU and battery reports")

    cap = sub.add_parser("capture", help="record passive telemetry without stressing the CPU")
    cap.add_argument("--duration", type=float, default=60)
    cap.add_argument("--interval", type=float, default=1)
    cap.add_argument("--filename", default="pulse_capture.csv")

    doctor = sub.add_parser("doctor", help="run tests, audits and a passive capture")
    doctor.add_argument("--duration", type=float, default=60)
    doctor.add_argument("--interval", type=float, default=1)

    args = parser.parse_args()
    report_dir = Path(args.report_dir).expanduser()

    if args.action == "selftest":
        return self_test()
    if args.action == "audit":
        return audit(report_dir)
    if args.action == "capture":
        if args.duration <= 0 or args.interval <= 0:
            parser.error("duration and interval must be positive")
        return capture(report_dir, args.duration, args.interval, args.filename)
    if args.action == "doctor":
        if args.duration <= 0 or args.interval <= 0:
            parser.error("duration and interval must be positive")
        code = self_test()
        code |= audit(report_dir)
        code |= capture(report_dir, args.duration, args.interval, "doctor_capture.csv")
        print("\nATOCIA doctor finished. Inspect the Markdown reports and CSV capture in:")
        print(report_dir)
        return code
    parser.error("unknown action")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
