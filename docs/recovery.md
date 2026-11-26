# neuDB failure recovery

Sources: `neudb/storage.py` and `neudb/table.py`.

## Interrupted writes

A table mutation writes a sibling `.<table>.json.*.tmp` file and then replaces the table file. An interruption before replacement leaves the previous table intact. An interruption after replacement leaves the new complete table. A crash can leave a stale temporary file, but reads ignore it.

Temporary files are not removed on open because another process could own one. Call `table.sweep_orphan_tmps(max_age_seconds=300)` explicitly while no other process is writing the directory. The method holds the same-process path lock and removes only matching files at least as old as the supplied age.

## Directory fsync and ambiguous errors

After `os.replace()`, neuDB fsyncs the parent directory on supporting POSIX filesystems so the rename can be persisted. Unsupported directory fsync is skipped. If a later fsync raises after replacement, the write may already be committed; neuDB surfaces the error. Reload the table before retrying an ambiguous write.

Atomic replacement prevents half-written JSON; it does not create a backup or guarantee survival of every power-loss or hardware failure.

## Corrupt or invalid data

`read_table_file()` raises `CorruptedTableError` for:

- invalid JSON or non-UTF-8 content;
- a top-level value that is not an object;
- invalid records, unsupported JSON values, or invalid IDs;
- a record whose `id` does not match its table key.

There is no automatic repair, checksum verification, backup rotation, or restore command. Stop writers, preserve the damaged files for diagnosis, and restore the table or database directory from your own backup.

## Operational guidance

- Back up the whole database directory while no process is writing it: `cp -r neudb_data neudb_data.backup`.
- Validate a copied table with `python -m json.tool neudb_data.backup/notes.json`.
- Treat a directory copy as a filesystem backup, not a transactional snapshot across tables.
- Sweep stale temp files only after confirming that no writer is active.

The test suite covers corruption handling, temp-file sweeping, and interrupted-write behavior. Power-loss torture tests and automated backup/restore tooling are not provided.
