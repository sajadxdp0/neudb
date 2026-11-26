# neuDB performance protocol

`benchmarks/bench.py` characterizes the full-file JSON design on the machine where it runs. It does not establish cross-machine performance guarantees or unsupported scaling comparisons.

## Run

From an installed checkout:

```bash
python benchmarks/bench.py --records 250 --vector-records 250 --vector-dim 32
python benchmarks/bench.py --records 250 --vector-records 250 --vector-dim 32 --json
```

The defaults are 2,000 document records, the same number of vector records, and 32 dimensions. Choose smaller inputs for a quick local run; every insert rewrites a complete table.

## Workloads

The script measures:

- individual document inserts, including throughput and p50/p95/mean latency;
- one `select_all()` full reload;
- one case-insensitive text search;
- one cosine similarity search over a separately built vector table;
- four same-process threads performing 100 inserts each into one table, with an expected final count of 400.

## Reproducibility

- Each run uses a `tempfile.TemporaryDirectory`, removed automatically when the run finishes or raises.
- Each run is one explicit trial (`trials: 1`), not a statistical sample.
- JSON output is a single result object containing metadata, document-table results, vector results, and threaded-write results.
- Metadata records the neuDB version, Python version and implementation, platform, Git commit when available, UTC timestamp, and trial count.
- Workload sizes and vector dimensions are included in the result so runs can be interpreted without guessing the input.

Save machine-readable output for comparison:

```bash
python benchmarks/bench.py --records 250 --json > benchmark.json
```

Interpret results in the context of the reported environment and commit. The structural cost is visible in the implementation: every read loads the full file and every write replaces it, so both grow with table size. The benchmark documents observed behavior; it does not prove multi-process safety, crash durability, or a fixed supported row count.
