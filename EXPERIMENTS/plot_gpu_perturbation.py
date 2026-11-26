#!/usr/bin/env python3
"""Plot ATOCIA GPU perturbation/recovery capture without resampling."""
from __future__ import annotations
import csv
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
CSV = ROOT / "ATOCIA_PERTURBATION_RECOVERY_2026-11-21.csv"
rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
t = [float(r["elapsed_s"]) for r in rows]

def series(column):
    xs, ys = [], []
    for x, row in zip(t, rows):
        value = row.get(column, "")
        try:
            y = float(value)
        except (TypeError, ValueError):
            continue
        xs.append(x)
        ys.append(y)
    return xs, ys

def save_plot(filename, items, ylabel, title):
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for column, label in items:
        xs, ys = series(column)
        if xs:
            ax.plot(xs, ys, label=label, linewidth=1.5)
    ax.axvspan(10, 18, alpha=0.16, label="Render window (scheduled)")
    ax.set_xlabel("Elapsed time (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(ROOT / filename, format="svg")
    plt.close(fig)

save_plot(
    "ATOCIA_PERTURBATION_GPU_ACTIVITY.svg",
    [("gpu_card1_gt_non_rc6_residency_pct", "GT non-RC6 proxy (%)")],
    "Activity proxy (%)",
    "Intel GT activity proxy — passive baseline / render / recovery",
)
save_plot(
    "ATOCIA_PERTURBATION_POWER.svg",
    [("msr_package_power_w", "Package power (MSR)"), ("psys_power_w", "PSys power")],
    "Power (W)",
    "Host energy domains — not isolated GPU power",
)
save_plot(
    "ATOCIA_PERTURBATION_TEMPERATURE.svg",
    [("temp_C_thermal_zone4_TCPU", "TCPU"), ("temp_C_thermal_zone5_x86_pkg_temp", "x86 package")],
    "Temperature (°C)",
    "Host CPU thermal response — not GPU temperature",
)
save_plot(
    "ATOCIA_PERTURBATION_CPU_LOAD.svg",
    [("cpu_util_pct", "CPU utilization")],
    "CPU utilization (%)",
    "CPU activity during graphics probe",
)
print("Generated 4 SVG plots in", ROOT)
