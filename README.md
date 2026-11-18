# neuDB

A database you can read with your own eyes.

Plain JSON tables, crash-atomic writes, and pure-Python text and cosine search. No server, no index, no dependencies — built for local prototypes and agents that need inspectable persistence.

Python · stdlib · JSON

## Install

```bash
pip install -e .
neudb table create users
neudb row insert users --data '{"username":"alice"}'
neudb row list users
```

## Test

```bash
pip install -e ".[test,api]" && pytest
```

Limits and guarantees are documented in [docs](docs/architecture.md).
