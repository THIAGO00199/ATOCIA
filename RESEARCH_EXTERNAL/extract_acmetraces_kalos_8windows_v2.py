#!/usr/bin/env python3
"""Build an expanded, timestamp-aligned AcmeTrace/Kalos pilot panel.

Uses only pre-audited HTTP byte ranges. The four new windows are Aug 25, 27,
28 and 30 2023; windows with zero cross-metric timestamp intersections are
intentionally excluded. The original four-window panel is not modified.
"""
from __future__ import annotations

import concurrent.futures
import csv
import gzip
import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PILOT = ROOT / "ACMETRACE_KALOS_PILOT"
META = ROOT / "metadata" / "acmetraces_kalos_timestamp_aligned_probe_v2.json"
OLD_PANEL = PILOT / "kalos_gpu_panel_4windows_v1.csv.gz"
OLD_REPORT = PILOT / "kalos_gpu_panel_4windows_v1_report.json"
OUT = PILOT / "kalos_gpu_panel_8windows_v2.csv.gz"
OUT_REPORT = PILOT / "kalos_gpu_panel_8windows_v2_report.json"

REPO = "Qinghao/AcmeTrace"
REVISION = "a484f7763a7812fc72eb49b8ba865b12fe7638e1"
BASE = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/data/utilization/kalos"
METRICS = ("POWER_USAGE", "GPU_TEMP", "GPU_UTIL")
UA = "ATOCIA-provenance-audit/1.0"

# Old target_window -> chronological window id in the expanded panel.
OLD_ID_MAP = {
    "2023-08-18T12:00:00+08:00": 1,
    "2023-08-22T12:00:00+08:00": 2,
    "2023-08-26T12:00:00+08:00": 4,
    "2023-08-29T12:00:00+08:00": 7,
}
NEW_ID_MAP = {
    "2023-08-25T12:00:00+08:00": 3,
    "2023-08-27T12:00:00+08:00": 5,
    "2023-08-28T12:00:00+08:00": 6,
    "2023-08-30T12:00:00+08:00": 8,
}


def get_range(metric: str, start: int, end: int):
    req = urllib.request.Request(
        f"{BASE}/{metric}.csv",
        headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=50) as response:
        if response.status != 206:
            raise RuntimeError(f"{metric}: expected HTTP 206, got {response.status}")
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
        if not match:
            raise RuntimeError(f"{metric}: invalid Content-Range")
        a, b, size = map(int, match.groups())
        if a != start or b > end:
            raise RuntimeError(f"{metric}: unexpected byte range {a}-{b}")
        data = response.read()
        if len(data) != b - a + 1:
            raise RuntimeError(f"{metric}: byte count mismatch")
        return data, size


def parse_rows(data: bytes, width: int):
    lines = data.decode("utf-8", "replace").splitlines()
    out = {}
    for row in csv.reader(io.StringIO("\n".join(lines[1:-1]))):
        if len(row) != width:
            continue
        try:
            ts = datetime.fromisoformat(row[0])
        except (ValueError, TypeError):
            continue
        out[ts] = row
    return out


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    meta = json.loads(META.read_text(encoding="utf-8"))
    old_report = json.loads(OLD_REPORT.read_text(encoding="utf-8"))

    # Only retain new windows with a nonempty intersection across all metrics.
    targets = [
        w for w in meta["per_window"]
        if w["common_timestamps"] > 0 and w["target_timestamp"] in NEW_ID_MAP
    ]
    if set(w["target_timestamp"] for w in targets) != set(NEW_ID_MAP):
        raise RuntimeError("The expected four new windows are not all available")

    headers, sizes = {}, {}
    for metric in METRICS:
        data, size = get_range(metric, 0, 65535)
        headers[metric] = next(csv.reader(io.StringIO(data.decode("utf-8", "replace"))))
        sizes[metric] = size
    ids = headers[METRICS[0]][1:]
    if len(ids) != 2344 or len(set(ids)) != 2344:
        raise RuntimeError("Unexpected GPU column count or duplicate identifiers")
    if any(set(headers[m][1:]) != set(ids) for m in METRICS[1:]):
        raise RuntimeError("GPU columns differ between metrics")

    devices = []
    for ident in ids:
        match = re.fullmatch(r"(\d{1,3}(?:\.\d{1,3}){3})-(\d+)", ident)
        if not match:
            raise RuntimeError("Unexpected GPU identifier format")
        host_ip = match.group(1)
        devices.append({
            "raw": ident,
            "gpu_hash": digest(ident)[:16],
            "host_hash": digest(host_ip)[:16],
            "gpu_index": int(match.group(2)),
        })
    indexes = {m: {ident: i for i, ident in enumerate(headers[m])} for m in METRICS}

    new_data = {}
    new_window_reports = {}
    downloaded = 0
    for w in sorted(targets, key=lambda x: x["target_timestamp"]):
        target = w["target_timestamp"]
        ranges = {
            item["metric"]: (item["start_byte"], item["end_byte"])
            for item in meta["range_details"] if item["target_timestamp"] == target
        }
        if set(ranges) != set(METRICS):
            raise RuntimeError(f"{target}: missing metric range")

        samples = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(get_range, metric, *ranges[metric]): metric
                for metric in METRICS
            }
            for fut in concurrent.futures.as_completed(futures):
                metric = futures[fut]
                data, size = fut.result()
                if size != sizes[metric]:
                    raise RuntimeError(f"{metric}: source file size changed")
                downloaded += len(data)
                samples[metric] = parse_rows(data, len(headers[metric]))

        common = sorted(
            set(samples[METRICS[0]]) & set(samples[METRICS[1]]) & set(samples[METRICS[2]])
        )
        if not common:
            raise RuntimeError(f"{target}: no common timestamps after exact parse")
        if common[0].isoformat() != w["first_common_timestamp"]:
            raise RuntimeError(f"{target}: first timestamp differs from audit")
        if common[-1].isoformat() != w["last_common_timestamp"]:
            raise RuntimeError(f"{target}: last timestamp differs from audit")
        if len(common) != w["common_timestamps"]:
            raise RuntimeError(f"{target}: common timestamp count differs from audit")

        rows = []
        counts_by_gpu = Counter()
        host_by_gpu = {}
        for ts in common:
            metric_rows = {m: samples[m][ts] for m in METRICS}
            for d in devices:
                vals = [metric_rows[m][indexes[m][d["raw"]]] for m in METRICS]
                if any(v == "" for v in vals):
                    continue
                try:
                    power, temp, util = map(float, vals)
                except ValueError:
                    continue
                if not all(map(lambda x: x == x and abs(x) != float("inf"), (power, temp, util))):
                    continue
                rows.append([
                    NEW_ID_MAP[target], target, ts.isoformat(),
                    d["gpu_hash"], d["host_hash"], d["gpu_index"],
                    power, temp, util,
                ])
                counts_by_gpu[d["gpu_hash"]] += 1
                host_by_gpu[d["gpu_hash"]] = d["host_hash"]

        expected = int(w["common_timestamps"]) * len(ids)
        interval = sorted(set(
            (b - a).total_seconds() for a, b in zip(common, common[1:])
        ))
        new_data[target] = rows
        new_window_reports[target] = {
            "common_timestamps": len(common),
            "first_timestamp": common[0].isoformat(),
            "last_timestamp": common[-1].isoformat(),
            "valid_triplet_rows": len(rows),
            "possible_triplets": expected,
            "coverage_fraction": len(rows) / expected if expected else None,
            "common_interval_seconds": interval,
            "gpu_entities_with_data": len(counts_by_gpu),
            "gpu_entities_with_complete_window": sum(
                n == len(common) for n in counts_by_gpu.values()
            ),
            "host_entities_with_data": len(set(host_by_gpu.values())),
        }

    # Rebuild the combined panel with chronological window IDs 1..8.
    header = [
        "window_id", "target_window", "timestamp",
        "gpu_id_hash", "host_id_hash", "gpu_index",
        "power_w", "gpu_temp_c", "gpu_util_pct",
    ]
    all_new_rows = 0
    with gzip.open(OUT, "wt", encoding="utf-8", newline="", compresslevel=6) as gz:
        writer = csv.writer(gz)
        writer.writerow(header)
        with gzip.open(OLD_PANEL, "rt", encoding="utf-8", newline="") as old:
            reader = csv.DictReader(old)
            for row in reader:
                old_target = row["target_window"]
                if old_target not in OLD_ID_MAP:
                    raise RuntimeError(f"Unexpected old panel target {old_target}")
                writer.writerow([
                    OLD_ID_MAP[old_target], row["target_window"], row["timestamp"],
                    row["gpu_id_hash"], row["host_id_hash"], row["gpu_index"],
                    row["power_w"], row["gpu_temp_c"], row["gpu_util_pct"],
                ])
                all_new_rows += 1
        for target in sorted(new_data):
            writer.writerows(new_data[target])
            all_new_rows += len(new_data[target])

    # Merge window metadata in chronological order.
    combined = {}
    for target, old_id in OLD_ID_MAP.items():
        info = old_report["windows"][target]
        combined[target] = {
            "common_timestamps": info["common_timestamps"],
            "first_timestamp": info["first_timestamp"],
            "last_timestamp": info["last_timestamp"],
            "valid_triplet_rows": info["valid_triplet_rows"],
            "possible_triplets": info["possible_triplets"],
            "coverage_fraction": info["coverage_fraction"],
            "common_interval_seconds": info["common_interval_seconds"],
        }
    for target, info in new_window_reports.items():
        combined[target] = info
    combined = dict(sorted(combined.items(), key=lambda kv: kv[1]["first_timestamp"]))

    report = {
        "dataset": "AcmeTrace / Kalos",
        "source_used_for_ranges": f"https://huggingface.co/datasets/{REPO}/tree/{REVISION}",
        "cross_mirror_reference": "HuggingAGree/AcmeTrace@19b38a000850a38cb39f9ee808c80cd6e39b20e7",
        "official_repository": "https://github.com/InternLM/AcmeTrace",
        "source_revision": REVISION,
        "metric_file_sizes_bytes": sizes,
        "gpu_columns": len(ids),
        "unique_hosts": len(set(d["host_hash"] for d in devices)),
        "window_count": len(combined),
        "windows": combined,
        "total_valid_triplet_rows": all_new_rows,
        "total_possible_triplet_rows": sum(x["possible_triplets"] for x in combined.values()),
        "overall_triplet_coverage": all_new_rows / sum(x["possible_triplets"] for x in combined.values()),
        "downloaded_new_range_bytes": downloaded,
        "output": str(OUT),
        "privacy_note": "Host/GPU IDs are deterministic unsalted SHA-256 pseudonyms, not guaranteed anonymization. Keep the panel internal; create keyed pseudonyms before external release.",
        "limits": [
            "Eight sparse, separated windows are not a representative six-month sample.",
            "All windows are from Kalos; cross-cluster or cross-hardware generalization is untested.",
            "The 15-second cadence does not support sub-second transient claims.",
            "Window IDs are chronological; gaps are never bridged.",
        ],
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT}")
    print(f"Wrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
