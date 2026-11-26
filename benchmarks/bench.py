"""Reproducible neuDB benchmarks with explicit workload metadata.

Examples:
    python benchmarks/bench.py --records 250
    python benchmarks/bench.py --records 250 --vector-records 250 --json

Every write rewrites a full JSON table and every read reloads it. These numbers
characterize that design on the current machine; they are not cross-machine
performance guarantees.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neudb import __version__, connect  # noqa: E402


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _pctl(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * quantile))]


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=_positive_int, default=2000)
    parser.add_argument(
        "--vector-records",
        type=_positive_int,
        help="vector table size (default: same as --records)",
    )
    parser.add_argument("--vector-dim", type=_positive_int, default=32)
    parser.add_argument("--json", action="store_true", help="emit one JSON result object")
    args = parser.parse_args()
    vector_records = args.vector_records or args.records

    with tempfile.TemporaryDirectory(prefix="neudb-bench-") as temporary:
        db = connect(temporary)
        table = db.table("docs")
        latencies: list[float] = []
        started = time.monotonic()
        for index in range(args.records):
            operation_started = time.monotonic()
            table.insert({"i": index, "text": f"record number {index} about python and databases"})
            latencies.append((time.monotonic() - operation_started) * 1000)
        insert_seconds = time.monotonic() - started

        started = time.monotonic()
        rows = table.select_all()
        read_ms = (time.monotonic() - started) * 1000

        started = time.monotonic()
        text_hits = table.search_text("text", "python", top_k=10)
        text_ms = (time.monotonic() - started) * 1000

        vector_table = db.table("vecs")
        for index in range(vector_records):
            vector_table.insert({"i": index, "embedding": [float(index % 7)] * args.vector_dim})
        query = [1.0] * args.vector_dim
        started = time.monotonic()
        vector_hits = vector_table.search_similar("embedding", query, top_k=10)
        vector_ms = (time.monotonic() - started) * 1000

        threaded_table = db.table("threaded")
        thread_errors: list[BaseException] = []
        errors_lock = threading.Lock()

        def write_batch() -> None:
            try:
                for _ in range(100):
                    threaded_table.insert({"x": 1})
            except BaseException as exc:  # propagate worker failures in the result
                with errors_lock:
                    thread_errors.append(exc)

        started = time.monotonic()
        threads = [threading.Thread(target=write_batch) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        threaded_seconds = time.monotonic() - started
        threaded_count = threaded_table.count()
        if thread_errors:
            raise RuntimeError(f"benchmark writer failed: {thread_errors[0]}")
        if threaded_count != 400:
            raise RuntimeError(f"benchmark expected 400 rows, got {threaded_count}")

        result = {
            "metadata": {
                "neudb_version": __version__,
                "python": platform.python_version(),
                "implementation": platform.python_implementation(),
                "platform": platform.platform(),
                "commit": _git_commit(),
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "trials": 1,
            },
            "table": {
                "records": args.records,
                "file_bytes": (Path(temporary) / "docs.json").stat().st_size,
                "insert_seconds": insert_seconds,
                "insert_records_per_second": args.records / insert_seconds,
                "insert_latency_ms": {
                    "p50": _pctl(latencies, 0.5),
                    "p95": _pctl(latencies, 0.95),
                    "mean": statistics.mean(latencies),
                },
                "read_all_ms": read_ms,
                "text_search_ms": text_ms,
                "text_search_hits": len(text_hits),
            },
            "vector": {
                "records": vector_records,
                "dimensions": args.vector_dim,
                "search_ms": vector_ms,
                "search_hits": len(vector_hits),
            },
            "threaded": {
                "threads": 4,
                "inserts_per_thread": 100,
                "seconds": threaded_seconds,
                "rows": threaded_count,
            },
        }
        if len(rows) != args.records:
            raise RuntimeError(f"benchmark expected {args.records} rows, got {len(rows)}")

    if args.json:
        print(json.dumps(result, indent=2))
        return
    metadata = result["metadata"]
    table_result = result["table"]
    latency = table_result["insert_latency_ms"]
    print(f"neuDB {metadata['neudb_version']} | Python {metadata['python']} | commit {metadata['commit']}")
    print(f"platform: {metadata['platform']}")
    print(
        f"insert({args.records}): {table_result['insert_records_per_second']:.0f} rec/s "
        f"p50={latency['p50']:.2f}ms p95={latency['p95']:.2f}ms mean={latency['mean']:.2f}ms"
    )
    print(f"read_all({args.records}): {read_ms:.1f}ms file={table_result['file_bytes']} bytes")
    print(f"text_search({args.records}): {text_ms:.1f}ms hits={len(text_hits)}")
    print(f"vector_search({vector_records}, dim={args.vector_dim}): {vector_ms:.1f}ms hits={len(vector_hits)}")
    print(f"threaded(4x100): {threaded_seconds:.2f}s rows={threaded_count}")


if __name__ == "__main__":
    main()
