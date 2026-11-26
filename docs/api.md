# neuDB HTTP API

The optional FastAPI application exposes the neuDB table engine over HTTP. It requires Python 3.11+, the `api` extra from `pyproject.toml`, and one server process.

## Start locally

From an installed GitHub checkout:

```bash
python -m pip install -e ".[api]"
export NEUDB_API_KEY='replace-with-a-long-random-value'
NEUDB_API_DB=neudb_api_data uvicorn neudb.api:app \
  --host 127.0.0.1 --port 8000
```

Do not run multiple API workers or replicas against the same directory. Storage locks are process-local only.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEUDB_API_DB` | `neudb_api_data` | Database directory. The app ensures the five AI memory tables exist. |
| `NEUDB_API_KEY` | unset | Single administrator credential. Protected routes return `503` until it is configured. |
| `NEUDB_MAX_REQUEST_BYTES` | `1048576` (1 MiB) | Streamed request-body limit, including chunked bodies. Minimum accepted value is 1024. |
| `NEUDB_CORS_ORIGINS` | `http://127.0.0.1:8080,http://localhost:8080` | Comma-separated browser origins allowed to call the API. |

`create_app(db_dir=..., api_key=...)` can supply the directory and key directly when embedding the application.

## Authentication and scope

Send the administrator key on every protected request:

```text
X-API-Key: your-key
```

A missing or incorrect key returns `401`. This is one shared administrator credential. The API is schemaless and does **not** provide per-user authorization, foreign keys, or username uniqueness. `/users`, `/sessions`, and `/messages` are convenience record shapes for the agent schema, not a multi-tenant security boundary.

## Health and readiness

These routes do not require the API key:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

- `GET /health` reports process status, version, and whether authentication is configured.
- `GET /ready` returns `200` only when the key is configured and the storage directory exists; otherwise it returns `503`.

## Tables and records

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/tables` | List table names. |
| `POST` | `/tables` | Create an empty table. |
| `GET` | `/tables/{table}/records` | List records with `limit` and `offset`. |
| `POST` | `/tables/{table}/records` | Insert a record. |
| `PATCH` | `/tables/{table}/records/{id}` | Merge fields into a record. |
| `DELETE` | `/tables/{table}/records/{id}` | Delete a record. |

There is no HTTP table-drop route. Table and field identifiers contain 1–128 ASCII letters, numbers, or underscores. API record path IDs are limited to 128 characters.

### Create a table and insert a record

```bash
curl -X POST http://127.0.0.1:8000/tables \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NEUDB_API_KEY" \
  -d '{"name":"notes"}'

curl -X POST http://127.0.0.1:8000/tables/notes/records \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NEUDB_API_KEY" \
  -d '{"title":"Python setup","done":false}'
```

Insert returns `201` with `{"id": "...", "record": {...}}`. If an existing ID is supplied, that record is replaced.

### List, update, and delete

```bash
curl "http://127.0.0.1:8000/tables/notes/records?limit=10&offset=0" \
  -H "X-API-Key: $NEUDB_API_KEY"

curl -X PATCH http://127.0.0.1:8000/tables/notes/records/RECORD_ID \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NEUDB_API_KEY" \
  -d '{"done":true}'

curl -X DELETE http://127.0.0.1:8000/tables/notes/records/RECORD_ID \
  -H "X-API-Key: $NEUDB_API_KEY"
```

List responses contain `records` and `total`. `limit` defaults to 100 and must be 1–1000; `offset` defaults to 0 and must be non-negative. Pagination happens after the full table is loaded. A patch cannot change `id`. Missing records return `404`.

## Agent-memory records

These routes write the standard `users`, `sessions`, and `messages` JSON tables. They do not validate that a session's user exists.

### Create a user and session

```bash
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NEUDB_API_KEY" \
  -d '{"username":"alice","email":"alice@example.com"}'

curl -X POST http://127.0.0.1:8000/sessions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NEUDB_API_KEY" \
  -d '{"user_id":"USER_ID","title":"Debugging Python"}'
```

Replace `USER_ID` with the returned ID. Usernames use the identifier rules; duplicate usernames are not rejected.

### Create and list messages

```bash
curl -X POST http://127.0.0.1:8000/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NEUDB_API_KEY" \
  -d '{"session_id":"SESSION_ID","role":"user","content":"How do I fix an import error?"}'

curl "http://127.0.0.1:8000/sessions/SESSION_ID/messages?limit=100&offset=0" \
  -H "X-API-Key: $NEUDB_API_KEY"
```

Replace `SESSION_ID` with the returned session ID. Message roles use the identifier rules and content is limited to 20,000 characters. If `embedding` is omitted, neuDB attempts to generate one; if the embeddings dependency is unavailable, the stored value is `null`. Model download or load errors are surfaced. Supply a finite numeric `embedding` array of at most 4,096 dimensions to skip generation. Session-message responses contain `messages` and `total` and use the same pagination limits as record lists.

## Search

`POST /search` accepts exactly one of `vector` or `query`:

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NEUDB_API_KEY" \
  -d '{"table":"messages","field":"embedding","vector":[0.12,0.84,-0.31],"top_k":5}'
```

| Field | Default | Meaning |
|-------|---------|---------|
| `table` | `messages` | Table to scan. |
| `field` | `embedding` | Vector field for vector or query search. |
| `text_field` | `content` | Text field used when `embed_text()` returns `None`. |
| `vector` | — | Finite numeric query vector, at most 4,096 dimensions. |
| `query` | — | Text to embed, at most 20,000 characters. |
| `top_k` | `5` | Result count, 1–100. |

A direct `vector` request performs local cosine similarity search. A `query` request first calls `embed_text()`; the first use downloads `all-MiniLM-L6-v2` if the `agent` or `embeddings` extra is installed. If embedding returns `None`, the API falls back to case-insensitive `search_text()` on `text_field`. The response is `{"results": [...]}` and does not include scores.

Providing both search fields or neither field returns `400`; invalid typed input and search limits return `422`. List-endpoint pagination outside its bounds returns `400`.

## Errors, CORS, and local dashboard use

- Request bodies over the configured limit return `413`, including streamed/chunked bodies.
- Corrupted table data or unavailable storage returns `503` without exposing filesystem details.
- CORS allows only the configured origins, `Content-Type` and `X-API-Key` headers, and the API's HTTP methods. Credentials are not enabled.
- The dashboard is local-only. If serving it from a different local port, add that exact origin to `NEUDB_CORS_ORIGINS`.
- An HTTPS page, including GitHub Pages, may be blocked from fetching an HTTP localhost API by mixed-content or Private Network Access rules. Serve the dashboard locally over HTTP for reliable use.

The API has no indexes, transactions, automatic backups, or multi-process safety. See [storage](storage.md), [concurrency](concurrency.md), and [search](search.md).
