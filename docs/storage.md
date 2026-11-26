# neuDB storage model

Sources: `neudb/database.py`, `neudb/table.py`, `neudb/storage.py`, and `neudb/config.py`.

## Files and records

- A database is a directory. A table is one UTF-8 JSON file named `<table>.json`.
- The top-level value is an object mapping record IDs to record objects. Each record's `id` must equal its table key.
- Table and field identifiers contain 1–128 ASCII letters, numbers, or underscores (`^[A-Za-z0-9_]+$`).
- A record ID is a non-empty string. IDs are immutable: `update()` rejects an `id` field, and `upsert()` preserves an existing record's ID.
- Values must round-trip through strict JSON: objects with string keys, arrays, strings, finite numbers, booleans, and `null`. NaN, infinity, circular references, unsupported Python objects, and excessive nesting are rejected.

Example `notes.json`:

```json
{
  "note-1": {
    "id": "note-1",
    "title": "Python setup",
    "done": false,
    "tags": ["local", "inspectable"]
  }
}
```

If `id` is omitted on insert, neuDB generates a UUID string. Supplying an existing ID to `insert()` intentionally replaces that record. `insert_many()` rejects duplicate IDs within the input batch and writes the batch in one snapshot. `upsert(record, keys)` matches records under the same process lock, merges fields, preserves the existing ID, and writes one snapshot.

## Read path

Every table operation reloads and validates the complete file. `select_all(limit=..., offset=...)` slices only after loading; `select_by()` compares fields using typed equality and never matches a missing field. Storage has no partial-read or paging mechanism, so reads are O(N) in table size.

## Atomic write path

1. Validate the complete new table snapshot.
2. Create a sibling `.<table>.json.*.tmp` file in the same directory.
3. Write formatted JSON, flush, and `fsync` the temporary file.
4. Replace the table file with `os.replace()`.
5. On supporting POSIX filesystems, open and `fsync` the parent directory to persist the rename.
6. Remove a leftover temporary file in the `finally` block.

The replace is atomic on supported filesystems: a reader sees the old complete file or the new complete file, never a partially written table. A single mutation, batch, or upsert is atomic for that one table; there are no multi-table transactions.

Directory fsync is best effort only where the filesystem supports it. An error after `os.replace()` is ambiguous: the new snapshot may already be committed even though the error is surfaced. Reload the table before retrying so a caller does not accidentally overwrite committed state.

## Deliberate limits

There are no indexes, checksums, compaction, WAL, automatic backups, or multi-process locks. Every write rewrites the entire table. The design favors inspectability and a dependency-free core over large-dataset throughput; use the [benchmark protocol](performance.md) to evaluate a specific workload.
