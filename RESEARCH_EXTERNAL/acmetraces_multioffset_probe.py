#!/usr/bin/env python3
"""Bounded, multi-offset coverage probe for AcmeTrace/Kalos DCGM matrices.

Fetches small HTTP Range windows only; never downloads a full CSV.
Identifiers are hashed in the report because headers contain private IPs.
"""
from __future__ import annotations

import concurrent.futures
import csv
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
OUT = ROOT / "metadata"
METRICS = ("POWER_USAGE", "GPU_TEMP", "GPU_UTIL")
BASE = "https://huggingface.co/datasets/Qinghao/AcmeTrace/resolve/main/data/utilization/kalos"
FRACTIONS = (0.04, 0.25, 0.50, 0.75, 0.96)
CHUNK_BYTES = 131072
UA = "ATOCIA-public-dataset-audit/1.0"


def get_range(metric: str, start: int, end: int) -> tuple[bytes, int, str]:
    url = f"{BASE}/{metric}.csv"
    req = urllib.request.Request(
        url,
        headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=40) as response:
        if response.status != 206:
            raise RuntimeError(f"{metric}: server ignored range (HTTP {response.status})")
        cr = response.headers.get("Content-Range", "")
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", cr)
        if not match:
            raise RuntimeError(f"{metric}: missing/invalid Content-Range: {cr!r}")
        a, b, total = map(int, match.groups())
        if a != start or b > end:
            raise RuntimeError(f"{metric}: unexpected range {cr}")
        data = response.read()
        if len(data) != b - a + 1:
            raise RuntimeError(f"{metric}: byte-count mismatch for {cr}: {len(data)}")
        return data, total, cr


def get_header(metric: str) -> tuple[list[str], int]:
    data, total, cr = get_range(metric, 0, 65535)
    text = data.decode("utf-8", "replace")
    header = next(csv.reader(io.StringIO(text)))
    if not header or header[0] != "Time":
        raise RuntimeError(f"{metric}: unexpected header")
    return header, total


def parse_window(data: bytes, expected_columns: int) -> dict[datetime, list[str]]:
    text = data.decode("utf-8", "replace")
    lines = text.splitlines()
    # At nonzero byte offsets, discard the first (possibly partial) line and
    # the last (possibly partial) line. This avoids fabricating observations.
    if len(lines) < 3:
        return {}
    reader = csv.reader(io.StringIO("\n".join(lines[1:-1])))
    result: dict[datetime, list[str]] = {}
    for row in reader:
        if len(row) != expected_columns:
            continue
        try:
            ts = datetime.fromisoformat(row[0])
        except (ValueError, TypeError):
            continue
        result[ts] = row
    return result


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    headers: dict[str, list[str]] = {}
    sizes: dict[str, int] = {}
    for metric in METRICS:
        headers[metric], sizes[metric] = get_header(metric)

    ref = headers[METRICS[0]]
    ref_set = set(ref[1:])
    if len(ref_set) != len(ref) - 1:
        raise RuntimeError("Duplicate identifiers in the POWER_USAGE header")
    for metric in METRICS[1:]:
        if set(headers[metric][1:]) != ref_set:
            raise RuntimeError(f"{metric} header IDs differ from POWER_USAGE")

    # Header format in the published matrix is host-IP plus GPU index.
    parsed_ids = []
    for ident in ref[1:]:
        m = re.fullmatch(r"(\d{1,3}(?:\.\d{1,3}){3})-(\d+)", ident)
        if not m:
            raise RuntimeError("GPU header format is not host-IP-GPU-index")
        parsed_ids.append((ident, m.group(1), int(m.group(2))))
    host_counts = Counter(host for _, host, _ in parsed_ids)

    jobs = []
    for metric in METRICS:
        for frac in FRACTIONS:
            start = min(max(0, int(sizes[metric] * frac)), sizes[metric] - CHUNK_BYTES - 1)
            jobs.append((metric, frac, start, start + CHUNK_BYTES - 1))

    samples: dict[float, dict[str, dict[datetime, list[str]]]] = {
        f: {m: {} for m in METRICS} for f in FRACTIONS
    }
    byte_checks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        future_map = {
            pool.submit(get_range, metric, start, end): (metric, frac, start, end)
            for metric, frac, start, end in jobs
        }
        for fut in concurrent.futures.as_completed(future_map):
            metric, frac, start, end = future_map[fut]
            data, total, cr = fut.result()
            if total != sizes[metric]:
                raise RuntimeError(f"{metric}: file size changed during probe")
            samples[frac][metric] = parse_window(data, len(headers[metric]))
            byte_checks.append({"metric": metric, "fraction": frac, "content_range": cr, "bytes": len(data)})

    per_window = []
    aggregate_counts: Counter[str] = Counter()
    aggregate_common_times = 0
    for frac in FRACTIONS:
        by_metric = samples[frac]
        time_sets = [set(by_metric[m]) for m in METRICS]
        common_times = set.intersection(*time_sets) if time_sets else set()
        ordered_times = sorted(common_times)
        gaps = [(b - a).total_seconds() for a, b in zip(ordered_times, ordered_times[1:])]
        counts: list[tuple[int, str]] = []
        idx = {m: {ident: i for i, ident in enumerate(headers[m])} for m in METRICS}
        for ident in ref[1:]:
            complete = 0
            for ts in common_times:
                if all(by_metric[m][ts][idx[m][ident]] != "" for m in METRICS):
                    complete += 1
            counts.append((complete, ident))
            aggregate_counts[ident] += complete
        counts.sort(reverse=True)
        n = len(common_times)
        aggregate_common_times += n
        per_window.append({
            "file_fraction": frac,
            "sampled_bytes_per_metric": CHUNK_BYTES,
            "valid_rows": {m: len(by_metric[m]) for m in METRICS},
            "per_metric_timestamp_ranges": {
                m: {
                    "first": min(by_metric[m]).isoformat() if by_metric[m] else None,
                    "last": max(by_metric[m]).isoformat() if by_metric[m] else None,
                }
                for m in METRICS
            },
            "first_common_timestamp": ordered_times[0].isoformat() if n else None,
            "last_common_timestamp": ordered_times[-1].isoformat() if n else None,
            "common_timestamps": n,
            "common_interval_seconds": sorted(set(gaps)),
            "best_gpu_hash": digest(counts[0][1]) if counts and n else None,
            "best_gpu_complete_triplets": counts[0][0] if counts and n else 0,
            "best_gpu_complete_fraction": counts[0][0] / n if n else None,
            "gpu_count_ge_80pct_complete": sum(c >= 0.8 * n for c, _ in counts) if n else 0,
            "gpu_count_ge_50pct_complete": sum(c >= 0.5 * n for c, _ in counts) if n else 0,
            "median_nonempty_cells_per_row": {
                m: statistics.median(
                    sum(v != "" for v in row[1:]) for row in by_metric[m].values()
                ) if by_metric[m] else None
                for m in METRICS
            },
        })

    ranked = sorted(aggregate_counts.items(), key=lambda kv: kv[1], reverse=True)
    report = {
        "dataset": "AcmeTrace / Kalos",
        "source": "https://huggingface.co/datasets/Qinghao/AcmeTrace",
        "official_repository": "https://github.com/InternLM/AcmeTrace",
        "method": "HTTP Range only; 5 distributed byte windows per metric; no full CSV downloaded.",
        "sampling_interval_documented_seconds": 15,
        "file_sizes_bytes": sizes,
        "metric_units_verified_from_official_data_utils_py": {
            "POWER_USAGE": "DCGM_FI_DEV_POWER_USAGE, W",
            "GPU_TEMP": "DCGM_FI_DEV_GPU_TEMP, degrees C",
            "GPU_UTIL": "DCGM_FI_DEV_GPU_UTIL, percent",
        },
        "gpu_column_identity": {
            "header_pattern": "host IPv4 address + '-' + GPU index",
            "gpu_columns": len(parsed_ids),
            "unique_hosts": len(host_counts),
            "gpu_columns_per_host_min": min(host_counts.values()),
            "gpu_columns_per_host_median": statistics.median(host_counts.values()),
            "gpu_columns_per_host_max": max(host_counts.values()),
        },
        "windows": per_window,
        "aggregate_best_gpu_hashes": [
            {"gpu_hash": digest(ident), "complete_triplets_across_sampled_windows": count}
            for ident, count in ranked[:20]
        ],
        "aggregate_common_timestamps_across_windows": aggregate_common_times,
        "downloaded_bytes_total": sum(x["bytes"] for x in byte_checks) + 3 * 65536,
        "range_checks": byte_checks,
        "limits": [
            "Distributed windows are a coverage probe, not a representative full-dataset sample.",
            "Byte fractions are approximate positions in the file; timestamps are measured from returned rows.",
            "No full six-month panel has been assembled; no model has been trained on AcmeTrace.",
            "Correlated observations and repeated host/GPU IDs require entity-aware chronological evaluation.",
        ],
    }
    target = OUT / "acmetraces_kalos_multioffset_probe_v1.json"
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
