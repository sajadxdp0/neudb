# neuDB engineering decisions

## Directory of JSON files

A database is a directory and a table is one formatted JSON object. This keeps the core dependency-free, makes data readable with ordinary tools, and makes filesystem backups straightforward. The trade-off is a full-file load on every read and a full-file rewrite on every mutation: O(N) cost with no indexes.

## Strict JSON and immutable string IDs

Records must round-trip through strict JSON, and each record ID must match its table key. Rejecting non-finite numbers, circular references, unsupported objects, and ID-changing updates prevents invalid state from being persisted. IDs are strings rather than database-managed relational keys.

## Atomic snapshot replacement

A sibling temporary file, flush, file `fsync`, and `os.replace()` provide single-table atomicity without a WAL. Supporting POSIX filesystems also fsync the parent directory to persist the rename. An fsync error after replacement remains ambiguous and is surfaced; callers reload before retrying. Batches and upserts use the same one-snapshot commit path.

## Process-local locking only

A per-path `threading.RLock` covers the common threaded, single-process use case without dependencies. Multi-process file locking is not provided because it would require a broader ownership and recovery protocol. Overlapping writers in different processes can lose updates; the API is single-process only.

## No indexes or transactions

Prototype and local-memory workloads favor a small, inspectable engine. Every filter and search is a scan. A single table mutation is atomic, but there are no multi-table transactions, isolation levels, WAL, or query planner.

## Optional interfaces

The core dependency list is empty. The `api`, `agent`/`embeddings`, `test`, and `dev` extras in `pyproject.toml` add FastAPI/Uvicorn, sentence-transformers, or development tools only when needed. Installation is from a GitHub checkout; there is no package-index distribution claim for 0.5.0.

## Convenience memory schema

The `users`, `sessions`, `messages`, `tags`, and `memories` tables are ordinary JSON tables. They make the agent's retrieve/inject/persist loop thin, but they do not add foreign keys, username uniqueness, or multi-tenant authorization.

## Explicitly out of scope

0.5.0 does not provide multi-process locks, indexes, transactions, automatic backups, corruption repair, or a fixed large-dataset row guarantee. Those are product boundaries, not unfinished placeholders.
