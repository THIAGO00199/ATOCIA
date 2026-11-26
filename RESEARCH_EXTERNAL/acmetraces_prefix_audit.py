#!/usr/bin/env python3
"""Reproducible prefix-only quality audit of AcmeTrace/Kalos matrices.

This reads only the bounded prefix files collected by the companion range
probe. It does not download full traces, does not infer undocumented units,
and does not expose private-looking host identifiers in the report.
"""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SAMPLE_DIR = ROOT / "metadata" / "acmetraces_samples"
METRICS = ("POWER_USAGE", "GPU_TEMP", "GPU_UTIL")


def load_prefix(metric: str) -> tuple[list[str], list[list[str]]]:
    path = SAMPLE_DIR / f"{metric}.prefix"
    if not path.is_file():
        raise FileNotFoundError(f"Missing range sample: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for row in reader if len(row) == len(header)]
    if not header or header[0] != "Time":
        raise ValueError(f"Unexpected first column in {metric}: {header[:1]}")
    return header, rows


def parse_timestamp(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def numeric_values(rows: list[list[str]]) -> list[float]:
    result = []
    for row in rows:
        for raw in row[1:]:
            if raw == "":
                continue
            try:
                result.append(float(raw))
            except ValueError:
                pass
    return result


def digest_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    tables = {name: load_prefix(name) for name in METRICS}
    header_sets = {name: set(value[0][1:]) for name, value in tables.items()}
    reference = header_sets[METRICS[0]]
    if any(s != reference for s in header_sets.values()):
        raise ValueError("Metric headers differ; do not align by column position.")
    if len(reference) != 2344:
        raise ValueError(f"Unexpected common GPU identifiers: {len(reference)}")

    timestamps_by_metric: dict[str, list[datetime]] = {}
    per_metric: dict[str, dict[str, Any]] = {}
    for name, (header, rows) in tables.items():
        times = [parse_timestamp(row[0]) for row in rows]
        deltas = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
        counts = [sum(raw != "" for raw in row[1:]) for row in rows]
        values = numeric_values(rows)
        timestamps_by_metric[name] = times
        per_metric[name] = {
            "complete_rows_in_prefix": len(rows),
            "first_timestamp": times[0].isoformat() if times else None,
            "last_timestamp": times[-1].isoformat() if times else None,
            "unique_intervals_seconds": sorted(set(deltas)),
            "median_nonempty_gpu_cells_per_row": (
                statistics.median(counts) if counts else None
            ),
            "gpu_identifiers_with_headers": len(header) - 1,
            "raw_values_count": len(values),
            "raw_min": min(values) if values else None,
            "raw_median": statistics.median(values) if values else None,
            "raw_max": max(values) if values else None,
        }

    time_sets = {name: set(values) for name, values in timestamps_by_metric.items()}
    common_times = set.intersection(*time_sets.values())
    row_maps = {
        name: {parse_timestamp(row[0]): row for row in tables[name][1]}
        for name in METRICS
    }
    common_gpu_ids = sorted(reference)
    indices = {
        name: {gpu: i for i, gpu in enumerate(tables[name][0])}
        for name in METRICS
    }

    coverage: list[tuple[int, str]] = []
    complete_triplets = 0
    for gpu in common_gpu_ids:
        count = 0
        for timestamp in common_times:
            cells = [
                row_maps[name][timestamp][indices[name][gpu]]
                for name in METRICS
            ]
            if all(value != "" for value in cells):
                count += 1
        coverage.append((count, gpu))
    coverage.sort(reverse=True)
    n_times = len(common_times)
    best_count, best_gpu = coverage[0] if coverage else (0, "")
    threshold = int(0.8 * n_times) if n_times else 0

    report = {
        "dataset": "AcmeTrace / Kalos utilization matrices",
        "source": "https://huggingface.co/datasets/HuggingAGree/AcmeTrace",
        "source_repository": "https://github.com/InternLM/AcmeTrace",
        "sampling_interval_documented_seconds": 15,
        "method": "Only 256 KiB prefixes of each CSV were read; no full trace was downloaded.",
        "common_gpu_identifiers": len(reference),
        "metric_headers_identical": True,
        "common_timestamps_across_all_three_metrics": n_times,
        "metrics": per_metric,
        "gpu_identifiers_with_at_least_80pct_complete_triplets_in_sample": sum(
            count >= threshold for count, _ in coverage
        ),
        "best_sample_gpu_identifier_hash": digest_id(best_gpu) if best_gpu else None,
        "best_sample_gpu_complete_triplets": best_count,
        "best_sample_gpu_complete_fraction": best_count / n_times if n_times else None,
        "interpretation_limits": [
            "Prefix-only sample, not representative of whole file or full six-month release.",
            "Raw units are not assigned: README identifies the metrics but does not state units in the inspected schema.",
            "Header identifiers look like private network IP plus GPU index; report hashes them rather than reproducing them.",
            "Sparse values may reflect inactive/unavailable devices; full-period availability must be measured before choosing a training series.",
            "15-second interval is unsuitable for validating sub-second power transients.",
            "Correlation across signals is not causal identification.",
        ],
    }
    out = ROOT / "metadata" / "acmetraces_prefix_quality_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
