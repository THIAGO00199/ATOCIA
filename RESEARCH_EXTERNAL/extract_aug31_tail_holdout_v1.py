#!/usr/bin/env python3
"""Extract an Aug 31 AcmeTrace/Kalos holdout from bounded EOF HTTP ranges."""
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
PROBE = ROOT / "metadata" / "acmetraces_kalos_aug31_tail_probe_v1.json"
OUT = PILOT / "kalos_gpu_panel_aug31_2023_holdout_v1.csv.gz"
REPORT = PILOT / "kalos_gpu_panel_aug31_2023_holdout_v1_report.json"
REVISION = "a484f7763a7812fc72eb49b8ba865b12fe7638e1"
BASE = f"https://huggingface.co/datasets/Qinghao/AcmeTrace/resolve/{REVISION}/data/utilization/kalos"
METRICS = ("POWER_USAGE", "GPU_TEMP", "GPU_UTIL")
UA = "ATOCIA-public-dataset-audit/1.0"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch(metric: str, start: int, end: int):
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
        if (a, b) != (start, end):
            raise RuntimeError(f"{metric}: unexpected Content-Range {a}-{b}")
        data = response.read()
        if len(data) != end - start + 1:
            raise RuntimeError(f"{metric}: response byte count mismatch")
        return data, size


def parse_tail(data: bytes, width: int):
    # At EOF, the first line can be partial, but subsequent complete lines
    # (including the final line) are safe to parse.
    lines = data.decode("utf-8", "replace").splitlines()
    output = {}
    for row in csv.reader(io.StringIO("\n".join(lines[1:]))):
        if len(row) != width:
            continue
        try:
            ts = datetime.fromisoformat(row[0])
        except (ValueError, TypeError):
            continue
        output[ts] = row
    return output


def main():
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    sizes = probe["file_sizes_bytes"]
    chunk = probe["chunk_bytes_per_metric"]
    headers = {}
    for metric in METRICS:
        req = urllib.request.Request(
            f"{BASE}/{metric}.csv",
            headers={"Range": "bytes=0-65535", "Accept-Encoding": "identity", "User-Agent": UA},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            headers[metric] = next(csv.reader(io.StringIO(response.read().decode("utf-8", "replace"))))
    ids = headers["POWER_USAGE"][1:]
    if len(ids) != 2344 or len(set(ids)) != 2344:
        raise RuntimeError("Unexpected GPU header identifiers")
    if any(set(headers[m][1:]) != set(ids) for m in METRICS):
        raise RuntimeError("GPU columns differ between metrics")
    index = {m: {ident: i for i, ident in enumerate(headers[m])} for m in METRICS}

    ranges = {m: (sizes[m] - chunk, sizes[m] - 1) for m in METRICS}
    samples = {}
    downloaded = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fetch, m, *ranges[m]): m for m in METRICS}
        for future in concurrent.futures.as_completed(futures):
            metric = futures[future]
            data, size = future.result()
            if size != sizes[metric]:
                raise RuntimeError("Source file size changed since probe")
            downloaded += len(data)
            samples[metric] = parse_tail(data, len(headers[metric]))

    common = sorted(set(samples["POWER_USAGE"]) & set(samples["GPU_TEMP"]) & set(samples["GPU_UTIL"]))
    if len(common) < 100:
        raise RuntimeError(f"Insufficient aligned timestamps: {len(common)}")
    gaps = sorted(set((b - a).total_seconds() for a, b in zip(common, common[1:])))
    if gaps != [15.0]:
        raise RuntimeError(f"Unexpected sampling cadence: {gaps}")

    records = []
    gpu_counts = Counter()
    hosts = set()
    with gzip.open(OUT, "wt", encoding="utf-8", newline="", compresslevel=6) as gz:
        writer = csv.writer(gz)
        writer.writerow([
            "target_window", "timestamp", "gpu_id_hash", "host_id_hash",
            "gpu_index", "power_w", "gpu_temp_c", "gpu_util_pct",
        ])
        for ts in common:
            rows = {m: samples[m][ts] for m in METRICS}
            for ident in ids:
                vals = [rows[m][index[m][ident]] for m in METRICS]
                if any(v == "" for v in vals):
                    continue
                try:
                    power, temp, util = map(float, vals)
                except ValueError:
                    continue
                match = re.fullmatch(r"(\d{1,3}(?:\.\d{1,3}){3})-(\d+)", ident)
                if not match:
                    raise RuntimeError("Unexpected GPU identity format")
                host_ip, gpu_idx = match.group(1), int(match.group(2))
                gh = sha(ident)[:16]
                hh = sha(host_ip)[:16]
                writer.writerow([
                    "2023-08-31", ts.isoformat(), gh, hh, gpu_idx,
                    power, temp, util,
                ])
                gpu_counts[gh] += 1
                hosts.add(hh)
                records.append(1)

    n = len(common)
    report = {
        "dataset": "AcmeTrace / Kalos",
        "source": f"https://huggingface.co/datasets/Qinghao/AcmeTrace/tree/{REVISION}",
        "source_revision": REVISION,
        "target_window": "2023-08-31",
        "first_timestamp": common[0].isoformat(),
        "last_timestamp": common[-1].isoformat(),
        "common_timestamps": n,
        "sampling_interval_seconds": 15,
        "common_interval_seconds": gaps,
        "gpu_columns_in_source": len(ids),
        "gpu_entities_with_data": len(gpu_counts),
        "gpu_entities_with_full_window": sum(v == n for v in gpu_counts.values()),
        "gpu_entities_with_partial_window": sum(0 < v < n for v in gpu_counts.values()),
        "unique_hosts_with_data": len(hosts),
        "complete_triplet_rows": len(records),
        "possible_triplet_rows": n * len(ids),
        "triplet_coverage_fraction": len(records) / (n * len(ids)),
        "range_bytes_per_metric": chunk,
        "total_downloaded_range_bytes_including_headers": downloaded + 3 * 65536,
        "ranges": {m: [ranges[m][0], ranges[m][1]] for m in METRICS},
        "output": str(OUT),
        "privacy_note": "Unsalted SHA-256 truncation is pseudonymization, not guaranteed anonymization. Do not publicly release persistent host/GPU hashes.",
        "role": "Separate final temporal holdout. Do not use this window for tuning or model selection.",
    }
    report["panel_sha256"] = hashlib.sha256(OUT.read_bytes()).hexdigest()
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT}\nWrote {REPORT}")


if __name__ == "__main__":
    main()
