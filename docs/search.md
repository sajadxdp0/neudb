# neuDB search

Sources: `neudb/search.py`, `neudb/table.py`, `neudb/ai_schema.py`, and `neudb/agent.py`.

## Text search

`Table.search_text(field, query, top_k=5)` scans every record and returns up to `top_k` records whose field contains `query`, case-insensitively. Field values are converted to text for matching. This is substring search, not tokenized full-text search: there is no ranking score, stemming, or index. An empty query or `top_k < 1` returns an empty list.

## Vector search

`Table.search_similar(field, query_vector, top_k=5)` performs a brute-force cosine similarity scan:

- The query must contain finite numbers and cannot contain booleans.
- Records missing the field, whose field is not a list, or whose vector has a different dimension or invalid values are skipped.
- Compatible records are ordered by descending cosine similarity; ties retain record order.
- Results are record dictionaries, not `(record, score)` pairs.
- A zero-norm vector has similarity `0.0`. `top_k < 1` returns an empty list.

`cosine_similarity(a, b)` validates equal-length finite vectors and raises `ValueError` for invalid input or mismatched dimensions.

Both methods reload the full table and scan it in memory. Text search is O(N); vector search is O(N·D), where D is the vector dimension. There is no HNSW, IVF, FAISS, or other vector index.

## Optional embeddings

`neudb.ai_schema.embed_text()` lazily loads `sentence-transformers/all-MiniLM-L6-v2`. Install either the `agent` or `embeddings` extra declared in `pyproject.toml`. The first embedding use downloads the model and requires network access; later uses load it from the local cache.

If the embeddings dependency is unavailable, `embed_text()` returns `None`. Model download or load errors are surfaced rather than treated as a missing dependency. Callers must handle the `None` case:

- The agent uses the current user's most recent messages when `embed_text()` returns `None` or vector search yields no matches.
- `POST /search` with `query` falls back to `search_text()` on `text_field` when `embed_text()` returns `None`.

Agent retrieval first resolves the session's `user_id` and only searches messages from that user's sessions. The HTTP API's user/session/message routes do not provide per-user authorization.

## Privacy and egress

Core text and vector search are local. Installing the embeddings extra and using it for the first time contacts the model download host. The Ollama client is restricted to localhost by default. The OpenAI client sends the system prompt, retrieved memory context, and current user message to OpenAI; do not use it with data that must remain on-machine.
