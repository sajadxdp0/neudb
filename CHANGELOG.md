# Changelog

## [0.5.0] - 2026-11-26

### Added
- Structured argparse CLI with `--db`, JSON output, pagination, record get/update, text search, and explicit table-drop confirmation.
- Atomic `Table.insert_many()` and `Table.upsert()` operations, `Table.get()`/`count()`, and boolean mutation results.
- Streamed API request-body limits, `/ready`, paginated session messages, typed request models, and stable 4xx/5xx responses.
- User-scoped agent retrieval, atomic chat-exchange persistence, bounded provider responses, and redirect/proxy hardening.
- Typed package marker, dynamic version metadata, Python 3.11–3.14 CI matrix, reproducible benchmarks, security/contribution docs, and non-root container tooling.
- Unified light/dark logo family, social card, source-first README, and corrected product documentation/website.

### Changed
- **BREAKING:** Minimum Python version is now 3.11.
- **BREAKING:** Records must be strict JSON values with non-empty string IDs matching their table keys; IDs are immutable.
- **BREAKING:** `Database.create_table()` is silent and returns a boolean; `Table.update()`/`delete()` return booleans.
- CLI record lists use JSON Lines by default; `--json` emits a single JSON document.
- Writes fsync the parent directory on supporting POSIX filesystems; API and agent extras declare bounded dependency ranges.

### Fixed
- Closed same-process table-creation and temp-sweep races.
- Prevented malformed records, non-finite values, circular references, and excessive nesting from corrupting table invariants.
- Prevented invalid API identifiers, oversized chunked bodies, non-finite vectors, and ID-changing patches from becoming server errors.
- Prevented cross-user agent-memory retrieval and provider credential forwarding through redirects or ambient proxies.
- Corrected stale installation, API, environment, branding, and performance documentation.

## [0.4.1] - 2026-07-02
### Security
- Restricted table and API field identifiers to prevent path traversal.
- Added atomic JSON writes with per-file process locks.
- Added API key protection for HTTP API endpoints.
- Added request size and search limit validation to the HTTP API.
- Hardened LLM memory prompts against prompt injection.
- Restricted Ollama client URLs to localhost by default.

### Added
- `Table.search_text()` full-text fallback for environments without embeddings.

## [0.4.0] – 2026-06-24
### Added
- Built-in semantic search via cosine similarity (pure Python).
- `Table.search_similar()` method and CLI `row search` command.
- `neudb.ai_schema` module with multi-user AI memory helpers.
- Automatic message embedding with `sentence-transformers` (optional).

## [0.3.0] – 2026-06-23
### Added
- Multi-user AI memory schema (users, sessions, messages, tags, memories).
- High-level helper functions: `add_user`, `create_session`, `add_message_with_embedding`, etc.

## [0.2.0] – 2026-06-22
### Added
- Core file-based storage engine (JSON per table).
- CLI interface: `table create`, `row insert/list/find/delete`.
- Library mode: `connect()`, `Table` class.

## [0.1.0] – 2025-06-21
- Conceptual design and schema definition.
