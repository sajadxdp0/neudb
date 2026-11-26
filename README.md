<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/logo.svg">
    <img alt="neuDB" src="docs/brand/logo-light.svg" width="240">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/sajadxdp0/neudb/actions/workflows/ci.yml"><img src="https://github.com/sajadxdp0/neudb/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-6D5BD0.svg" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-6D5BD0.svg" alt="Python 3.11 or newer">
  <a href="https://sajadxdp0.github.io/neudb/"><img src="https://img.shields.io/badge/Website-neuDB-17171C.svg" alt="neuDB website"></a>
</p>

**Inspectable embedded Python storage with atomic JSON tables, text search, and vector search.**

neuDB 0.5.0 is a small, source-first storage library for local tools, prototypes, and LLM-agent memory. A database is a directory; each table is a formatted JSON file you can read with `cat`, inspect with `git diff`, and copy with ordinary filesystem tools. The core uses only the Python standard library.

This is embedded storage for one process, not PostgreSQL or a server database. It has no indexes, transactions, automatic backups, or multi-process locks. Those limits are part of the design and are documented below.

## Features

- **Inspectable JSON tables.** Strict JSON records with immutable string IDs in human-readable files.
- **Atomic mutations.** Inserts, batches, upserts, updates, and deletes replace a complete table snapshot atomically.
- **Text and vector search.** Case-insensitive substring search and brute-force cosine similarity in pure Python.
- **Four interfaces.** Python library, CLI, optional single-process HTTP API, and an optional LLM-agent memory loop.
- **Zero-dependency core.** Python 3.11+; install only the API, agent/embeddings, test, or development extras you need.

## Install from source

Install neuDB from a GitHub checkout. This release does not use a package-index install command.

```bash
git clone https://github.com/sajadxdp0/neudb.git
cd neudb
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1`.

Optional extras are defined in `pyproject.toml`:

```bash
python -m pip install -e ".[api]"          # FastAPI and Uvicorn
python -m pip install -e ".[agent]"        # agent dependencies, including embeddings
python -m pip install -e ".[embeddings]"   # sentence-transformers only
python -m pip install -e ".[test]"         # test dependencies
python -m pip install -e ".[dev]"          # development tools
```

## Quickstarts

### Python library

```python
from neudb import connect

db = connect("neudb_data")
db.create_table("notes")
notes = db.table("notes")

note_id = notes.insert(
    {
        "title": "Python setup",
        "done": False,
        "embedding": [0.12, 0.84, -0.31],
    }
)
notes.insert_many(
    [
        {"title": "Atomic JSON writes", "done": True},
        {"title": "Local vector search", "done": False},
    ]
)
notes.upsert({"slug": "setup", "done": True}, keys=("slug",))

print(notes.get(note_id))
print(notes.select_by("done", True))
print(notes.select_all(limit=10, offset=0))
print(notes.search_text("title", "python"))
print(notes.search_similar("embedding", [0.10, 0.80, -0.30], top_k=3))

notes.update(note_id, {"done": True})
print(notes.exists(note_id), notes.count())
notes.delete(note_id)
```

The table interface is `insert`, `insert_many`, `upsert`, `get`, `select_all`, `select_by`, `update`, `delete`, `exists`, `count`, `search_similar`, and `search_text`. Records must contain only strict JSON values. IDs are non-empty strings, match their table keys, and cannot be changed by `update`.

### CLI

Global options come before the subcommand. The CLI reads `NEUDB_DB` or defaults to `neudb_data`.

```bash
neudb --db ./neudb_data table create notes
neudb --db ./neudb_data --json row insert notes \
  --data '{"title":"Python setup","done":false}'
neudb --db ./neudb_data row list notes --limit 10 --offset 0
neudb --db ./neudb_data row get notes --id RECORD_ID
neudb --db ./neudb_data row find notes --where done=false
neudb --db ./neudb_data row update notes --id RECORD_ID \
  --data '{"done":true}'
neudb --db ./neudb_data row search-text notes \
  --field title --query python --top-k 5
neudb --db ./neudb_data row delete notes --id RECORD_ID
neudb --db ./neudb_data table list
```

`row list` and `row find` emit JSON Lines by default; `--json` emits one JSON document. See the [CLI guide](docs/cli.md) for vector search and all commands.

### HTTP API

```bash
python -m pip install -e ".[api]"
export NEUDB_API_KEY='replace-with-a-long-random-value'
NEUDB_API_DB=neudb_api_data uvicorn neudb.api:app \
  --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready

curl -X POST http://127.0.0.1:8000/tables \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NEUDB_API_KEY" \
  -d '{"name":"notes"}'

curl -X POST http://127.0.0.1:8000/tables/notes/records \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NEUDB_API_KEY" \
  -d '{"title":"Python setup","done":false}'
```

Run one server process only. `X-API-Key` is a single administrator credential, not a multi-tenant authorization system; the API does not enforce foreign keys or username uniqueness. See the [API guide](docs/api.md).

### LLM-agent memory

The agent uses Ollama on localhost by default. Install the agent extra, pull a model, and start the chat loop:

```bash
python -m pip install -e ".[agent]"
ollama pull llama3.2
neudb-agent --provider ollama --model llama3.2 --db ./agent_memory
```

For OpenAI, content sent to the provider leaves your machine:

```bash
export OPENAI_API_KEY='your-provider-key'
neudb-agent --provider openai --model gpt-4o-mini --db ./agent_memory
```

The first embedding use downloads `all-MiniLM-L6-v2`. If the embeddings dependency is unavailable, `embed_text()` returns `None`; the agent falls back to the current user's recent messages, while API query search falls back to `search_text`. Model download or load errors are surfaced. Retrieval is scoped to the session user. See [Search](docs/search.md) and [Product scope](docs/PRODUCT.md).

## Guarantees and limits

| Area | Guarantee | Limit |
|------|-----------|-------|
| Format | One UTF-8 JSON object per table; records contain strict JSON values; IDs are immutable non-empty strings matching their keys. | Schemaless records; no relational constraints or migrations. |
| Atomicity | Each mutation writes a sibling temp file, flushes and `fsync`s it, then uses `os.replace`. Batches and upserts commit as one table snapshot. | Not a transaction across tables. |
| Durability | Supporting POSIX filesystems also `fsync` the parent directory after replacement to persist the rename. | Filesystem and hardware dependent; no backup or power-loss guarantee. An fsync error after replacement is an ambiguous committed write: reload before retrying. |
| Concurrency | Per-path reentrant locks serialize threads within one process. | No multi-process or cross-machine locking; overlapping writers can lose updates. |
| Complexity | Simple, inspectable full-file storage. | Reads and writes load/rewrite the whole table: O(N). No fixed supported row count. |
| Search | Deterministic full scans for substring and cosine similarity. | No indexes; text search is O(N), vector search is O(N·D). |
| Recovery | Invalid data raises `CorruptedTableError`; stale temp files can be swept explicitly. | No automatic repair, checksums, backups, or restore command. |
| HTTP API | Optional FastAPI interface with one `X-API-Key` administrator credential and request-size limits. | Single process only; no multi-tenant authorization, foreign keys, or username uniqueness. |
| Intended use | Local tools, prototypes, and LLM-agent memory. | Not a PostgreSQL replacement or a production/server database. |

## Data-directory defaults

| Interface | Setting | Default |
|-----------|---------|---------|
| Library `connect(dir)` | `dir` argument | `neudb_data` |
| CLI `--db` | `NEUDB_DB` | `neudb_data` |
| API | `NEUDB_API_DB` | `neudb_api_data` |
| Agent CLI `--db` | `--db` argument | `neudb_agent_memory` |
| AI schema `init_ai_database(dir)` | `dir` argument | `ai_memory` |

## Documentation

- [Documentation index](docs/README.md)
- [Architecture](docs/architecture.md) · [Storage](docs/storage.md) · [Recovery](docs/recovery.md)
- [Concurrency](docs/concurrency.md) · [Search](docs/search.md) · [Decisions](docs/decisions.md)
- [CLI](docs/cli.md) · [API](docs/api.md) · [Product scope](docs/PRODUCT.md)
- [Performance protocol](docs/performance.md) · [Brand assets](docs/brand/README.md)
- [Website](https://sajadxdp0.github.io/neudb/) · [Changelog](CHANGELOG.md)
- [Coding-assistant demo](demos/realworld_coding_assistant.py) (run with explicit `--reset` to replace its demo data)

## Development and contributing

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
mypy
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. See the [Code of Conduct](CODE_OF_CONDUCT.md), [security policy](SECURITY.md), and [issue tracker](https://github.com/sajadxdp0/neudb/issues). The reproducible benchmark protocol is documented in [docs/performance.md](docs/performance.md).

## License

[MIT](LICENSE).

<details>
<summary>Hashtags and topics</summary>

#neuDB #Python #Database #JSON #VectorSearch #AIMemory #LLM #OpenSource #EmbeddedDatabase #DeveloperTools

</details>
