# neuDB concurrency

Source: `neudb/config.py`, with locking used by `neudb/database.py`, `neudb/table.py`, and `neudb/storage.py`.

## Same-process threads

neuDB keeps a reentrant `threading.RLock` for each resolved table path. Table creation, dropping, reads, searches, and mutations acquire that lock. Writers reload inside the lock, build a complete snapshot, and replace the file while still holding it. This serializes same-process access across multiple `Table` handles for the same path.

`insert_many()` and `upsert()` perform matching and replacement under one lock, so a batch or upsert commits as one table snapshot within the process.

## Multiple processes

There is no `fcntl`/`flock` lock, interprocess coordination, or cross-machine synchronization. Two processes writing the same table can lose updates: each reloads an older snapshot and the last replacement wins. Atomic file replacement prevents partial JSON, but it does not prevent lost updates.

Do not share a database directory between processes when writes may overlap. Run the optional HTTP API as one process only; multiple workers or replicas are not supported. External scheduling, rolling deployments, and multi-host access are outside the storage contract.

## Transactions and isolation

There are no transactions, isolation levels, WAL, or replay. Each table mutation is atomic for one file. A sequence of library calls is not an atomic unit, and a failure partway through a multi-table workflow can leave earlier table changes committed.

The tests exercise same-process threaded writers and readers. Multi-process writers are intentionally unsupported rather than treated as a safe configuration.
