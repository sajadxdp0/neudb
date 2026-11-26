# Contributing to neuDB

Thanks for helping improve neuDB: inspectable embedded Python storage with
atomic JSON tables, text search, and vector search. It is intended for local
tools, prototypes, and LLM-agent memory—not as a PostgreSQL or server-database
replacement.

## Development setup

Requirements: **Python 3.11+**, [uv](https://docs.astral.sh/uv/), and Git.

```bash
git clone https://github.com/sajadxdp0/neudb.git
cd neudb
uv sync --locked --extra dev
```

The core library has no runtime dependencies. The `dev` extra includes the API,
test, typing, formatting, build, and audit tools. Embedding support is optional;
the default test suite does not download a model. Install the project from
GitHub or a source checkout—there is no PyPI release.

Useful commands:

```bash
make install     # sync the locked development environment
make test        # run pytest
make lint        # Ruff lint
make format      # apply Ruff formatting
make typecheck   # mypy
make build       # build sdist and wheel in dist/
make audit       # audit the locked development dependency set
make bench       # run the storage benchmark
make demo        # run the local coding-assistant demo
make web         # serve website/ at http://127.0.0.1:8080
```

Optional pre-commit hooks: run `uvx pre-commit install`. The hooks check
whitespace, YAML, and large files, and run Ruff.

## Before opening a pull request

1. Add or update regression tests for behavior changes. Keep tests deterministic,
   local, and independent of Ollama or model downloads.
2. Run `make lint`, `make typecheck`, and `make test`. Run `make format` if Ruff
   reports formatting changes.
3. Update the relevant documentation for user-visible changes.
4. Add a concise entry under **Unreleased** in `CHANGELOG.md` for fixes,
   features, or compatibility changes.
5. Use the pull-request template to describe verification and compatibility.
   Never commit `.env` files, API keys, generated databases, or build artifacts.

## Compatibility policy

- Python 3.11 and newer are supported; CI covers 3.11, 3.12, 3.13, and 3.14.
- The core remains standard-library-only. API and agent/embedding dependencies
  stay in optional extras.
- Public library, CLI, and API changes should be additive within the 0.5.x line.
  Bug fixes may change incorrect behavior, but must be documented.
- Breaking changes require a clear rationale, migration notes, and maintainer
  agreement. neuDB is pre-1.0, so do not assume changes are risk-free.
- On-disk table format changes must preserve or migrate existing data safely.
- The HTTP API supports one process and local deployment. Do not introduce a
  multi-process/server-database architecture without an explicit design decision.

Keep pull requests focused and explain the problem before the implementation.
