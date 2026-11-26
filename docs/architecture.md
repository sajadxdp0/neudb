# neuDB architecture

neuDB is a Python 3.11+ library whose core uses only the standard library. The package under `neudb/` is the implementation; the top-level `neudb.py` module is a compatibility entry point.

## Layers

```text
Python library: neudb/__init__.py → connect() → Database → Table
                                              │
CLI: neudb/cli.py ─────────────────────────────┤
Optional API: neudb/api.py ────────────────────┤
Optional agent: neudb/agent.py ────────────────┤
                                              ↓
Table: one {id: record} JSON file per table in a database directory
                                              ↓
neudb/storage.py: validated full-file reads and atomic snapshot writes
neudb/config.py: identifier validation and process-local path locks
```

- **Database** manages a directory and table paths. `create_table()` returns a boolean and is silent on an existing table; `drop_table()` returns whether a file existed.
- **Table** implements record CRUD, typed equality filters, pagination, text search, and cosine similarity search. Every operation reloads the full table file.
- **Storage** validates strict JSON and ID invariants, writes a sibling temporary file, fsyncs it, and atomically replaces the table file. Supporting POSIX filesystems also fsync the parent directory.
- **CLI** exposes the same operations through global `--db` and `--json` options.
- **API** is an optional FastAPI application over the same database, protected by one administrator API key and restricted to one server process.
- **Agent** stores `users`, `sessions`, `messages`, `tags`, and `memories` through the table API. It retrieves only messages belonging to the current session user.
- **Website dashboard** is a static browser client for a locally running API. It is not part of the storage engine.

## Request paths

- Library: `connect(dir)` → `Database.table(name)` → table operations.
- CLI: `neudb [--db DIR] [--json] table …` and `neudb [--db DIR] [--json] row …`.
- HTTP: `GET /health`, `GET /ready`, `GET/POST /tables`, `GET/POST /tables/{table}/records`, `PATCH/DELETE /tables/{table}/records/{id}`, `POST /users`, `POST /sessions`, `POST /messages`, `GET /sessions/{id}/messages`, and `POST /search`.
- Search: a vector request calls `Table.search_similar(field, vector)`. A query request embeds the text when possible and otherwise calls `Table.search_text(text_field, query)`.

`/health` reports process status. `/ready` checks that authentication and the storage directory are available. Other routes require `X-API-Key`. The user/session/message routes are convenience record shapes, not relational constraints or multi-tenant authorization.

## Data directories

| Interface | Default |
|-----------|---------|
| `connect(dir)` | `neudb_data` |
| CLI `--db` | `NEUDB_DB` or `neudb_data` |
| API `NEUDB_API_DB` | `neudb_api_data` |
| Agent CLI `--db` | `neudb_agent_memory` |
| `init_ai_database(dir)` | `ai_memory` |

## Intentional boundaries

There is no server process for core library use, query planner, index, WAL, transaction manager, backup system, or multi-process coordination. Reads and writes are O(N) full-file operations. See [storage](storage.md), [concurrency](concurrency.md), [recovery](recovery.md), and [decisions](decisions.md).
