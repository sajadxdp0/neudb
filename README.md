# neuDB

A database you can read with your own eyes.

neuDB is embedded storage for local prototypes and AI agents that need inspectable persistence without running PostgreSQL. Each table is a plain JSON file, writes are crash-atomic, and search is pure Python. It is deliberately small: no server, no index, no transactions.

## Features

- Human-readable JSON tables; `cat` is the debugger
- Crash-atomic writes using a temp file, fsync, and atomic replace
- Text and cosine similarity search in the standard library
- CLI for creating tables and managing rows
- Optional FastAPI layer with API-key auth
- Optional AI memory schema for users, sessions, messages, and memories

## Stack

Python · standard library · JSON

## Quick start

```bash
pip install -e .
neudb table create users
neudb row insert users --data '{"username":"alice"}'
neudb row list users
```

## Tests

```bash
pip install -e ".[test,api]" && pytest
```

## Documentation

[Architecture](docs/architecture.md) · [Storage](docs/storage.md) · [Search](docs/search.md) · [Promo site](https://sajadxdp0.github.io/neudb/)
