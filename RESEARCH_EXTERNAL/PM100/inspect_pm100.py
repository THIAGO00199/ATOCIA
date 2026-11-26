#!/usr/bin/env python3
"""Low-impact metadata/sample audit for the PM100 Parquet release.

This tool deliberately does not train a model. It inspects the PM100 v1 file
using one DuckDB thread and a 512 MiB memory cap, then writes only compact
metadata and a tiny example sequence. It preserves the source Parquet file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

EXPECTED_MD5 = "2a692d9b9dc4a6ee4bc5e3eb3d0fa6f5"
SAMPLE_INTERVAL_SECONDS = 20


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("job_table.parquet"))
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("audit"))
    parser.add_argument("--max-rows", type=int, default=20000,
                        help="Maximum number of jobs to inspect (default: 20000; use 0 for all).")
    parser.add_argument("--memory-limit", default="512MB")
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 2
    if args.max_rows < 0:
        print("ERROR: --max-rows must be >= 0", file=sys.stderr)
        return 2

    try:
        import duckdb
    except ImportError:
        print("DuckDB is not installed. Create an isolated venv and run: pip install duckdb",
              file=sys.stderr)
        return 3

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print("Checking source file hashes...")
    actual_md5 = md5_file(args.input)
    actual_sha256 = sha256_file(args.input)
    if actual_md5 != EXPECTED_MD5:
        print(f"ERROR: MD5 mismatch: expected {EXPECTED_MD5}, got {actual_md5}", file=sys.stderr)
        return 4

    print("Opening Parquet with 1 thread and bounded memory...")
    con = duckdb.connect(
        database=":memory:",
        config={"threads": "1", "memory_limit": args.memory_limit},
    )
    source = str(args.input.resolve()).replace("'", "''")
    relation = f"read_parquet('{source}')"

    schema_rows = con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()
    schema = [{"column": row[0], "type": row[1], "null": row[2]} for row in schema_rows]
    (args.output_dir / "schema.json").write_text(
        json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    required = {"job_id", "start_time", "end_time", "run_time",
                "num_gpus_alloc", "power_consumption"}
    names = {item["column"] for item in schema}
    missing = sorted(required - names)
    if missing:
        print(f"ERROR: unexpected schema; missing columns: {missing}", file=sys.stderr)
        return 5

    total_rows = con.execute(f"SELECT COUNT(*) FROM {relation}").fetchone()[0]
    selected_rows = total_rows if args.max_rows == 0 else min(total_rows, args.max_rows)
    limit_sql = "" if args.max_rows == 0 else f" LIMIT {args.max_rows}"
    query = (
        "SELECT job_id, start_time, end_time, run_time, num_gpus_alloc, "
        f"power_consumption FROM {relation}{limit_sql}"
    )
    cursor = con.execute(query)

    job_count = 0
    gpu_job_count = 0
    empty_sequences = 0
    sample_count = 0
    lengths: list[int] = []
    values_min = math.inf
    values_max = -math.inf
    values_sum = 0.0
    values_n = 0
    sample_written = 0
    length_ge_10 = 0
    length_ge_30 = 0
    length_ge_60 = 0
    gpu_jobs_ge_30 = 0
    sample_limit = 3

    sample_path = args.output_dir / "sample_sequences.csv"
    with sample_path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["job_id", "start_time", "sample_index", "offset_seconds",
                         "node_power_raw", "num_gpus_alloc"])
        while True:
            rows = cursor.fetchmany(512)
            if not rows:
                break
            for job_id, start_time, end_time, run_time, num_gpus, power_seq in rows:
                job_count += 1
                if isinstance(num_gpus, (int, float)) and num_gpus > 0:
                    gpu_job_count += 1
                if power_seq is None:
                    empty_sequences += 1
                    continue
                seq = list(power_seq)
                if not seq:
                    empty_sequences += 1
                    continue
                lengths.append(len(seq))
                if len(seq) >= 10:
                    length_ge_10 += 1
                if len(seq) >= 30:
                    length_ge_30 += 1
                    if isinstance(num_gpus, (int, float)) and num_gpus > 0:
                        gpu_jobs_ge_30 += 1
                if len(seq) >= 60:
                    length_ge_60 += 1
                sample_count += len(seq)
                for raw in seq:
                    if raw is None:
                        continue
                    value = float(raw)
                    if not math.isfinite(value):
                        continue
                    values_min = min(values_min, value)
                    values_max = max(values_max, value)
                    values_sum += value
                    values_n += 1
                if sample_written < sample_limit:
                    for idx, raw in enumerate(seq):
                        writer.writerow([
                            job_id, json_safe(start_time), idx,
                            idx * SAMPLE_INTERVAL_SECONDS, raw, num_gpus
                        ])
                    sample_written += 1

    report = {
        "dataset": "PM100 v1",
        "doi": "10.5281/zenodo.8129258",
        "license": "CC BY 4.0",
        "source_file": args.input.name,
        "bytes": args.input.stat().st_size,
        "md5_expected": EXPECTED_MD5,
        "md5_actual": actual_md5,
        "md5_verified": actual_md5 == EXPECTED_MD5,
        "sha256": actual_sha256,
        "declared_sampling_interval_seconds": SAMPLE_INTERVAL_SECONDS,
        "power_unit": "W",
        "power_unit_basis": "M100 metric mapping identifies psX_input_power as Watts; PM100 sums both PSU input sensors across allocated nodes. See https://github.com/am-i-helpful/hpc-ontology-modeller and PM100 paper DOI 10.1145/3624062.3624263.",
        "parquet_rows_total": int(total_rows),
        "jobs_inspected": job_count,
        "gpu_jobs_inspected": gpu_job_count,
        "jobs_without_node_power_sequence": empty_sequences,
        "power_samples_inspected": sample_count,
        "sequence_length_min": min(lengths) if lengths else None,
        "sequence_length_median": statistics.median(lengths) if lengths else None,
        "sequence_length_mean": statistics.mean(lengths) if lengths else None,
        "sequence_length_max": max(lengths) if lengths else None,
        "jobs_with_at_least_10_samples": length_ge_10,
        "jobs_with_at_least_30_samples": length_ge_30,
        "jobs_with_at_least_60_samples": length_ge_60,
        "gpu_jobs_with_at_least_30_samples": gpu_jobs_ge_30,
        "node_power_raw_min": values_min if values_n else None,
        "node_power_raw_max": values_max if values_n else None,
        "node_power_raw_mean": values_sum / values_n if values_n else None,
        "power_values_counted": values_n,
        "max_rows_requested": args.max_rows,
        "interpretation_guardrail": (
            "Values are in watts according to the M100 metric mapping and are "
            "the sum of both PSU input-power sensors across all nodes allocated "
            "to a job. This is job-level aggregate node power, not isolated GPU power."
        ),
    }
    (args.output_dir / "audit_summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote: {args.output_dir / 'schema.json'}")
    print(f"Wrote: {args.output_dir / 'audit_summary.json'}")
    print(f"Wrote: {sample_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
