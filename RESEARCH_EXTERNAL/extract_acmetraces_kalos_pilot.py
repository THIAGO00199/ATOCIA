#!/usr/bin/env python3
"""Extract a small timestamp-aligned AcmeTrace/Kalos GPU panel from saved ranges."""
from __future__ import annotations

import concurrent.futures
import csv
import gzip
import hashlib
import io
import json
import re
import statistics
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
META = ROOT / "metadata" / "acmetraces_kalos_timestamp_aligned_probe_v1.json"
OUT_DIR = ROOT / "ACMETRACE_KALOS_PILOT"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "kalos_gpu_panel_4windows_v1.csv.gz"
METRICS = ("POWER_USAGE", "GPU_TEMP", "GPU_UTIL")
BASE = "https://huggingface.co/datasets/Qinghao/AcmeTrace/resolve/main/data/utilization/kalos"
UA = "ATOCIA-public-dataset-audit/1.0"


def digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def get_range(metric: str, start: int, end: int):
    req = urllib.request.Request(
        f"{BASE}/{metric}.csv",
        headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=50) as response:
        if response.status != 206:
            raise RuntimeError(f"{metric}: HTTP {response.status}; range not honored")
        m = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
        if not m:
            raise RuntimeError(f"{metric}: invalid Content-Range")
        a, b, total = map(int, m.groups())
        if a != start or b > end:
            raise RuntimeError(f"{metric}: returned unexpected range")
        data = response.read()
        if len(data) != b - a + 1:
            raise RuntimeError(f"{metric}: truncated range")
        return data, total


def parse_rows(data: bytes, width: int):
    lines = data.decode("utf-8", "replace").splitlines()
    out = {}
    # All saved offsets are nonzero positions within CSV bodies, so omit the
    # first and last possibly partial rows.
    for row in csv.reader(io.StringIO("\n".join(lines[1:-1]))):
        if len(row) != width:
            continue
        try:
            ts = datetime.fromisoformat(row[0])
        except (ValueError, TypeError):
            continue
        out[ts] = row
    return out


def main():
    meta = json.loads(META.read_text(encoding="utf-8"))
    headers, sizes = {}, {}
    for metric in METRICS:
        req = urllib.request.Request(
            f"{BASE}/{metric}.csv",
            headers={"Range": "bytes=0-65535", "Accept-Encoding": "identity", "User-Agent": UA},
        )
        with urllib.request.urlopen(req, timeout=40) as response:
            if response.status != 206:
                raise RuntimeError(f"{metric}: cannot fetch header by range")
            data = response.read()
            sizes[metric] = int(response.headers.get("Content-Range", "").split("/")[-1])
        headers[metric] = next(csv.reader(io.StringIO(data.decode("utf-8", "replace"))))
    ids = headers[METRICS[0]][1:]
    if len(ids) != 2344 or len(set(ids)) != len(ids):
        raise RuntimeError("Unexpected GPU header identifiers")
    for metric in METRICS[1:]:
        if set(headers[metric][1:]) != set(ids):
            raise RuntimeError("Metric headers differ; refusing positional alignment")

    indexes = {m: {ident: i for i, ident in enumerate(headers[m])} for m in METRICS}
    anonymized = []
    for ident in ids:
        m = re.fullmatch(r"(\d{1,3}(?:\.\d{1,3}){3})-(\d+)", ident)
        if not m:
            raise RuntimeError("Unexpected GPU identifier format")
        anonymized.append({
            "raw": ident,
            "gpu_hash": digest(ident),
            "host_hash": digest(m.group(1)),
            "gpu_index": int(m.group(2)),
        })

    ranges = meta["range_details"]
    grouped = {}
    for item in ranges:
        grouped.setdefault(item["target_timestamp"], {})[item["metric"]] = (item["start_byte"], item["end_byte"])
    if len(grouped) != 4 or any(set(g) != set(METRICS) for g in grouped.values()):
        raise RuntimeError("Expected exactly four complete timestamp-aligned windows")

    row_counts = {}
    value_stats = {m: [] for m in METRICS}
    triplet_count_by_gpu = Counter()
    total_possible = 0
    downloaded_bytes = 0

    with gzip.open(OUT, "wt", encoding="utf-8", newline="", compresslevel=6) as gz:
        writer = csv.writer(gz)
        writer.writerow([
            "window_id", "target_window", "timestamp",
            "gpu_id_hash", "host_id_hash", "gpu_index",
            "power_w", "gpu_temp_c", "gpu_util_pct",
        ])
        for window_id, target in enumerate(sorted(grouped), start=1):
            byte_ranges = grouped[target]
            samples = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                futures = {
                    pool.submit(get_range, metric, *byte_ranges[metric]): metric
                    for metric in METRICS
                }
                for future in concurrent.futures.as_completed(futures):
                    metric = futures[future]
                    data, size = future.result()
                    if size != sizes[metric]:
                        raise RuntimeError("File size changed since the probe")
                    downloaded_bytes += len(data)
                    samples[metric] = parse_rows(data, len(headers[metric]))
            common = sorted(
                set(samples[METRICS[0]]) & set(samples[METRICS[1]]) & set(samples[METRICS[2]])
            )
            total_possible += len(common) * len(ids)
            written = 0
            for ts in common:
                rows = {m: samples[m][ts] for m in METRICS}
                for device in anonymized:
                    ident = device["raw"]
                    vals = [rows[m][indexes[m][ident]] for m in METRICS]
                    if any(v == "" for v in vals):
                        continue
                    try:
                        power, temp, util = map(float, vals)
                    except ValueError:
                        continue
                    if not all(map(lambda x: x == x and abs(x) != float("inf"), (power, temp, util))):
                        continue
                    writer.writerow([
                        window_id, target, ts.isoformat(),
                        device["gpu_hash"], device["host_hash"], device["gpu_index"],
                        power, temp, util,
                    ])
                    value_stats["POWER_USAGE"].append(power)
                    value_stats["GPU_TEMP"].append(temp)
                    value_stats["GPU_UTIL"].append(util)
                    triplet_count_by_gpu[device["gpu_hash"]] += 1
                    written += 1
            row_counts[target] = {
                "common_timestamps": len(common),
                "first_timestamp": common[0].isoformat() if common else None,
                "last_timestamp": common[-1].isoformat() if common else None,
                "valid_triplet_rows": written,
                "possible_triplets": len(common) * len(ids),
                "coverage_fraction": written / (len(common) * len(ids)) if common else None,
                "common_interval_seconds": sorted(set(
                    (b-a).total_seconds() for a,b in zip(common, common[1:])
                )),
            }

    report = {
        "dataset": "AcmeTrace / Kalos",
        "source": "https://huggingface.co/datasets/Qinghao/AcmeTrace",
        "method": "Only the 12 previously verified HTTP byte ranges were fetched; full CSV files were not downloaded.",
        "file_sizes_bytes": sizes,
        "downloaded_csv_bytes": downloaded_bytes,
        "gpu_columns": len(ids),
        "unique_hosts": len(set(x["host_hash"] for x in anonymized)),
        "window_count": len(row_counts),
        "windows": row_counts,
        "total_valid_triplet_rows": sum(x["valid_triplet_rows"] for x in row_counts.values()),
        "total_possible_triplet_rows": total_possible,
        "overall_triplet_coverage": (
            sum(x["valid_triplet_rows"] for x in row_counts.values()) / total_possible
            if total_possible else None
        ),
        "gpu_entities_with_at_least_one_complete_triplet": len(triplet_count_by_gpu),
        "gpu_entities_with_100pct_triplets_in_extracted_panel": sum(
            count == sum(x["common_timestamps"] for x in row_counts.values())
            for count in triplet_count_by_gpu.values()
        ),
        "value_ranges": {
            m: {
                "min": min(v),
                "median": statistics.median(v),
                "max": max(v),
                "n": len(v),
            } for m, v in value_stats.items()
        },
        "output": str(OUT),
        "privacy": "IP-based GPU identifiers are SHA-256 hashed; raw host/IP identifiers are not written to the panel.",
        "limits": [
            "Four sparse time windows only; do not treat as a full-period or representative cluster sample.",
            "15-second sampling limits claims to slower dynamics, not sub-second transients.",
            "No predictive model has been trained by this extractor.",
        ],
    }
    report_path = OUT_DIR / "kalos_gpu_panel_4windows_v1_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
