# neuDB — product documentation

> **Inspectable embedded Python storage with atomic JSON tables, text search, and vector search.**

## Product

neuDB 0.5.0 is a source-first Python library for local tools, prototypes, and LLM-agent memory. A database is a directory of human-readable JSON files. The core requires Python 3.11+ and has no dependencies.

It is not PostgreSQL, a hosted database, or a server DBMS. It is designed for one process and small local datasets, with no indexes, transactions, automatic backups, or multi-process locks.

**Audience:** Python developers who want inspectable persistence without operating a database server.

## Install

Install from a GitHub checkout in a virtual environment:

```bash
git clone https://github.com/sajadxdp0/neudb.git
cd neudb
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Add only the extras declared in `pyproject.toml` that you need: `api`, `agent` or `embeddings`, `test`, or `dev`.

## Interfaces

### Library

`connect(dir)` returns a `Database`. Use `table()`, `create_table()`, `drop_table()`, and `list_tables()` to manage tables. A `Table` provides `insert`, `insert_many`, `upsert`, `get`, `select_all`, `select_by`, `update`, `delete`, `exists`, `count`, `search_similar`, and `search_text`.

```python
from neudb import connect

db = connect("neudb_data")
db.create_table("notes")
notes = db.table("notes")
note_id = notes.insert({"title": "Local memory", "done": False})
notes.update(note_id, {"done": True})
print(notes.select_all(limit=10, offset=0))
```

`create_table()` is silent and returns a boolean. `update()` and `delete()` return booleans. `select_by()` uses typed equality and does not match missing fields.

### CLI

Global `--db` and `--json` options precede the command. Table commands are `create`, `list`, and `drop`; row commands are `insert`, `list`, `get`, `find`, `update`, `delete`, `search`, and `search-text`. See [cli.md](cli.md).

### HTTP API

The optional FastAPI application exposes `/health`, `/ready`, table and record routes, `/users`, `/sessions`, `/messages`, `/sessions/{id}/messages`, and `/search`. All routes except health and readiness require the `X-API-Key` administrator credential.

The API is schemaless and single-process. It does not enforce foreign keys or username uniqueness, and its convenience user/session/message shapes are not a multi-tenant authorization system. See [api.md](api.md).

### Agent

`neudb-agent` runs a local chat loop backed by the standard memory tables. Ollama is restricted to localhost by default. OpenAI sends content off-machine. The first embedding use downloads `all-MiniLM-L6-v2`; if the embeddings dependency is unavailable, retrieval falls back to recent messages. Model download or load errors are surfaced. Retrieval is scoped to the session user.

## Data-directory defaults

| Interface | Setting | Default |
|-----------|---------|---------|
| Library `connect(dir)` | `dir` argument | `neudb_data` |
| CLI `--db` | `NEUDB_DB` | `neudb_data` |
| API | `NEUDB_API_DB` | `neudb_api_data` |
| Agent CLI `--db` | `--db` argument | `neudb_agent_memory` |
| AI schema `init_ai_database(dir)` | `dir` argument | `ai_memory` |

## Guarantees and operations

- Records are strict JSON with immutable, non-empty string IDs that match their table keys.
- Every mutation atomically replaces one complete table snapshot. Supporting POSIX filesystems also fsync the directory after replacement.
- An fsync error after replacement is ambiguous; reload before retrying.
- Reads and writes are O(N) full-file operations. Filters and searches are full scans; there are no indexes.
- Per-path locks cover threads in one process only. Overlapping multi-process writers can lose updates.
- There are no transactions, automatic backups, checksums, or repair commands. Back up the database directory while no writer is active.

See [storage.md](storage.md), [recovery.md](recovery.md), [concurrency.md](concurrency.md), and [search.md](search.md) for details.

## Privacy and egress

Core storage and search stay local. Embedding setup downloads a model on first use. Ollama stays on localhost unless explicitly allowed by a developer using the client API. OpenAI receives the prompt, retrieved memory, and current message. The static dashboard sends its API key only to the API URL entered by the user and is intended for local use.

## Development

Use the extras in `pyproject.toml`; follow [CONTRIBUTING.md](../CONTRIBUTING.md) and the [benchmark protocol](performance.md). The coding-assistant demo requires explicit `--reset` before replacing its demo data.
