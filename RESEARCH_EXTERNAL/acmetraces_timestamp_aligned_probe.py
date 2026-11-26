#!/usr/bin/env python3
"""Timestamp-aligned, bounded HTTP Range samples for AcmeTrace/Kalos."""
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
PREVIOUS = OUT / "acmetraces_kalos_multioffset_probe_v1.json"
METRICS = ("POWER_USAGE", "GPU_TEMP", "GPU_UTIL")
BASE = "https://huggingface.co/datasets/Qinghao/AcmeTrace/resolve/main/data/utilization/kalos"
TARGETS = (
    "2023-08-23T12:00:00+08:00",
    "2023-08-24T12:00:00+08:00",
    "2023-08-25T12:00:00+08:00",
    "2023-08-27T12:00:00+08:00",
    "2023-08-28T12:00:00+08:00",
    "2023-08-30T12:00:00+08:00",
)
CHUNK_BYTES = 2 * 1024 * 1024
UA = "ATOCIA-public-dataset-audit/1.0"


def get_range(metric: str, start: int, end: int):
    req = urllib.request.Request(
        f"{BASE}/{metric}.csv",
        headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=50) as response:
        if response.status != 206:
            raise RuntimeError(f"{metric}: HTTP {response.status}; Range not honored")
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
        if not match:
            raise RuntimeError(f"{metric}: invalid Content-Range")
        a, b, size = map(int, match.groups())
        if a != start or b > end:
            raise RuntimeError(f"{metric}: wrong byte interval {a}-{b}")
        data = response.read()
        if len(data) != b - a + 1:
            raise RuntimeError(f"{metric}: truncated range response")
        return data, size


def parse_rows(data: bytes, width: int):
    lines = data.decode("utf-8", "replace").splitlines()
    if len(lines) < 3:
        return {}
    output = {}
    for row in csv.reader(io.StringIO("\n".join(lines[1:-1]))):
        if len(row) != width:
            continue
        try:
            ts = datetime.fromisoformat(row[0])
        except (ValueError, TypeError):
            continue
        output[ts] = row
    return output


def digest(value: str):
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def epoch(dt: datetime):
    return dt.timestamp()


def main():
    prior = json.loads(PREVIOUS.read_text(encoding="utf-8"))
    anchors = {}
    for metric in METRICS:
        points = []
        for w in prior["windows"]:
            span = w["per_metric_timestamp_ranges"][metric]
            a = datetime.fromisoformat(span["first"])
            b = datetime.fromisoformat(span["last"])
            center = datetime.fromtimestamp((epoch(a) + epoch(b)) / 2, a.tzinfo)
            points.append((w["file_fraction"], center))
        anchors[metric] = sorted(points)

    headers, sizes = {}, {}
    for metric in METRICS:
        data, size = get_range(metric, 0, 65535)
        headers[metric] = next(csv.reader(io.StringIO(data.decode("utf-8", "replace"))))
        sizes[metric] = size
    ids = headers[METRICS[0]][1:]
    if len(set(ids)) != len(ids) or any(set(headers[m][1:]) != set(ids) for m in METRICS[1:]):
        raise RuntimeError("Metric headers are not identical and unique")

    # Use piecewise-linear interpolation from measured (byte fraction, timestamp)
    # anchors to estimate the byte offset for each common target timestamp.
    requests_to_make = []
    offsets_used = {}
    for target_raw in TARGETS:
        target = datetime.fromisoformat(target_raw)
        for metric in METRICS:
            pts = anchors[metric]
            t = epoch(target)
            bracket = None
            for left, right in zip(pts, pts[1:]):
                if epoch(left[1]) <= t <= epoch(right[1]):
                    bracket = (left, right)
                    break
            if bracket is None:
                raise RuntimeError(f"{metric}: no interpolation bracket for {target_raw}")
            (f0, t0), (f1, t1) = bracket
            frac = f0 + (f1 - f0) * ((t - epoch(t0)) / (epoch(t1) - epoch(t0)))
            center = int(frac * sizes[metric])
            start = max(0, min(center - CHUNK_BYTES // 2, sizes[metric] - CHUNK_BYTES - 1))
            end = start + CHUNK_BYTES - 1
            offsets_used[(target_raw, metric)] = {"estimated_fraction": frac, "start": start, "end": end}
            requests_to_make.append((target_raw, metric, start, end))

    samples = {target: {m: {} for m in METRICS} for target in TARGETS}
    byte_total = 0
    range_details = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        fm = {
            pool.submit(get_range, metric, start, end): (target, metric, start, end)
            for target, metric, start, end in requests_to_make
        }
        for fut in concurrent.futures.as_completed(fm):
            target, metric, start, end = fm[fut]
            data, actual_size = fut.result()
            if actual_size != sizes[metric]:
                raise RuntimeError("file size changed within one audit")
            samples[target][metric] = parse_rows(data, len(headers[metric]))
            byte_total += len(data)
            range_details.append({
                "target_timestamp": target, "metric": metric,
                "start_byte": start, "end_byte": end, "bytes": len(data),
                "estimated_fraction": offsets_used[(target, metric)]["estimated_fraction"],
            })

    per_window = []
    aggregate_counts = Counter()
    aggregate_total = 0
    for target in TARGETS:
        by_metric = samples[target]
        time_sets = [set(by_metric[m]) for m in METRICS]
        common = set.intersection(*time_sets)
        ordered = sorted(common)
        gaps = [(b-a).total_seconds() for a,b in zip(ordered, ordered[1:])]
        indexes = {m: {ident:i for i,ident in enumerate(headers[m])} for m in METRICS}
        ranked = []
        for ident in ids:
            n_complete = 0
            for ts in common:
                if all(by_metric[m][ts][indexes[m][ident]] != "" for m in METRICS):
                    n_complete += 1
            ranked.append((n_complete, ident))
            aggregate_counts[ident] += n_complete
        ranked.sort(reverse=True)
        n = len(common)
        aggregate_total += n
        per_window.append({
            "target_timestamp": target,
            "valid_rows": {m: len(by_metric[m]) for m in METRICS},
            "per_metric_timestamp_ranges": {
                m: {
                    "first": min(by_metric[m]).isoformat() if by_metric[m] else None,
                    "last": max(by_metric[m]).isoformat() if by_metric[m] else None,
                } for m in METRICS
            },
            "common_timestamps": n,
            "first_common_timestamp": ordered[0].isoformat() if n else None,
            "last_common_timestamp": ordered[-1].isoformat() if n else None,
            "common_interval_seconds": sorted(set(gaps)),
            "best_gpu_hash": digest(ranked[0][1]) if n else None,
            "best_gpu_complete_triplets": ranked[0][0] if n else 0,
            "best_gpu_complete_fraction": ranked[0][0] / n if n else None,
            "gpu_count_ge_80pct_complete": sum(c >= .8*n for c,_ in ranked) if n else 0,
            "gpu_count_ge_50pct_complete": sum(c >= .5*n for c,_ in ranked) if n else 0,
            "median_nonempty_cells_per_row": {
                m: statistics.median(sum(v != "" for v in row[1:]) for row in by_metric[m].values())
                if by_metric[m] else None for m in METRICS
            },
        })

    ranked_all = sorted(aggregate_counts.items(), key=lambda kv: kv[1], reverse=True)
    report = {
        "dataset": "AcmeTrace / Kalos",
        "method": "Timestamp-aligned HTTP Range windows estimated from five distributed byte/time anchors; no full CSV download.",
        "target_windows": list(TARGETS),
        "chunk_bytes_per_metric_per_window": CHUNK_BYTES,
        "file_sizes_bytes": sizes,
        "gpu_columns": len(ids),
        "common_gpu_columns": len(set.intersection(*(set(headers[m][1:]) for m in METRICS))),
        "per_window": per_window,
        "aggregate_common_timestamps": aggregate_total,
        "aggregate_best_gpu_hashes": [
            {"gpu_hash": digest(ident), "complete_triplets": count}
            for ident, count in ranked_all[:20]
        ],
        "downloaded_data_bytes": byte_total,
        "range_details": range_details,
        "limits": [
            "This is still a sparse coverage probe, not a full six-month panel.",
            "Offsets are estimated from a piecewise-linear byte/time map; actual timestamps are retained and exact intersections measured.",
            "No model has been trained and no prediction advantage is claimed.",
        ],
    }
    out = OUT / "acmetraces_kalos_timestamp_aligned_probe_v2.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
