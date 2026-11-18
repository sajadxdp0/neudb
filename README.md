# neuDB

**Zero-dependency embedded Python database with human-readable JSON tables, crash-atomic writes, and vector search.**

neuDB is small, inspectable persistence for local prototypes and LLM agents that do not warrant running PostgreSQL or a vector server. Each table is a single formatted JSON file on disk, writes are crash-atomic, and text and cosine similarity search run in pure Python. Its limits are stated up front: no server, no secondary indexes, no multi-process locks, and an O(N) full-file rewrite ceiling around ~10K rows per table.

## Design notes

- **Inspectable on-disk format.** A database is a directory; a table is `<name>.json` mapping string IDs to records. `cat` and `git diff` work as debugging tools without a client binary.
- **Crash-atomic single-file writes.** Mutations write to a sibling `.tmp` file, flush and `fsync` the file descriptor, and swap it into place with `os.replace`. Interrupted writes leave the previous table intact, and stray temp files can be swept on recovery.
- **In-process thread safety.** Per-path `threading.RLock` guards concurrent readers and writers within one Python process (verified by an 8-thread × 25-insert stress test).
- **Zero-dependency core, optional extras.** The storage engine uses only the Python standard library (`dependencies = []` in `pyproject.toml`). Optional extras add a FastAPI HTTP layer (`[api]`) and an AI agent memory schema (`[agent]`).

## Stack

Python 3.10+ · standard library (`json`, `os`, `threading`, `math`) · optional FastAPI & sentence-transformers extras

## Where to look

- `neudb/storage.py` & `neudb/table.py` — validated reads, `temp` + `fsync` + `os.replace` writes, and table CRUD
- `neudb/search.py` — pure-Python substring and cosine similarity search
- `neudb/api.py` — optional FastAPI server with API-key auth and request-size limits
- `neudb/ai_schema.py` & `neudb/agent.py` — structured memory tables (`users`, `sessions`, `messages`, `memories`) for LLM agents
- `tests/test_recovery.py` & `tests/test_concurrency.py` — corruption handling, temp-file sweeping, and thread-safety tests

## Quick start

```bash
pip install -e .

# CLI
neudb table create users
neudb row insert users --data '{"username": "alice", "role": "engineer"}'
neudb row list users
```

```python
import neudb

db = neudb.connect("mydata")
items = db.table("items")
items.insert({"title": "spec", "embedding": [0.12, 0.84, -0.31]})
matches = items.search_similar("embedding", [0.10, 0.80, -0.30], top_k=3)
```

## Testing

```bash
pip install -e ".[test,api]" && pytest -q
```

All 32 tests cover CRUD, atomic persistence, search, HTTP endpoints, agent memory schemas, thread concurrency, and corruption recovery.

## Documentation

[Architecture](docs/architecture.md) · [Storage & guarantees](docs/storage.md) · [Recovery](docs/recovery.md) · [Concurrency](docs/concurrency.md) · [Search](docs/search.md) · [Promo site](https://sajadxdp0.github.io/neudb/)

MIT License.
