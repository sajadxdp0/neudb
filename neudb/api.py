"""Optional FastAPI REST API for neuDB."""

import hmac
import logging
import os
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi import Path as ApiPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import ai_schema
from ._version import __version__
from .config import IDENTIFIER_PATTERN
from .database import Database
from .errors import CorruptedTableError

logger = logging.getLogger(__name__)

DEFAULT_API_DB_DIR = "neudb_api_data"
DEFAULT_MAX_REQUEST_BYTES = 1_048_576
MAX_TEXT_LENGTH = 20_000
MAX_VECTOR_DIMENSIONS = 4096
MAX_TOP_K = 100
MAX_RECORD_ID_LENGTH = 128


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class TableCreate(InputModel):
    name: str = Field(min_length=1, max_length=128, pattern=IDENTIFIER_PATTERN)


class UserCreate(InputModel):
    username: str = Field(min_length=1, max_length=128, pattern=IDENTIFIER_PATTERN)
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    display_name: str | None = Field(default=None, max_length=256)
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=50)


class SessionCreate(InputModel):
    user_id: str = Field(min_length=1, max_length=MAX_RECORD_ID_LENGTH)
    title: str = Field(min_length=1, max_length=512)
    description: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    model: str = Field(default="", max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=50)


class MessageCreate(InputModel):
    session_id: str = Field(min_length=1, max_length=MAX_RECORD_ID_LENGTH)
    role: str = Field(min_length=1, max_length=32, pattern=IDENTIFIER_PATTERN)
    content: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    embedding: list[float] | None = Field(default=None, min_length=1, max_length=MAX_VECTOR_DIMENSIONS)
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=50)


class SearchRequest(InputModel):
    table: str = Field(default="messages", pattern=IDENTIFIER_PATTERN, max_length=128)
    field: str = Field(default="embedding", pattern=IDENTIFIER_PATTERN, max_length=128)
    text_field: str = Field(default="content", pattern=IDENTIFIER_PATTERN, max_length=128)
    query: str | None = Field(default=None, min_length=1, max_length=MAX_TEXT_LENGTH)
    vector: list[float] | None = Field(default=None, min_length=1, max_length=MAX_VECTOR_DIMENSIONS)
    top_k: int = Field(default=5, ge=1, le=MAX_TOP_K)


class RequestBodyLimitMiddleware:
    """Count streamed request bytes before FastAPI parses JSON."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope["headers"]:
            if name.lower() != b"content-length":
                continue
            try:
                declared = int(value.decode("ascii"))
            except (UnicodeDecodeError, ValueError):
                response = JSONResponse(status_code=400, content={"detail": "Invalid Content-Length."})
                await response(scope, receive, send)
                return
            if declared < 0:
                response = JSONResponse(status_code=400, content={"detail": "Invalid Content-Length."})
                await response(scope, receive, send)
                return
            if declared > self.max_bytes:
                response = JSONResponse(status_code=413, content={"detail": "Request body too large."})
                await response(scope, receive, send)
                return
            break

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                response = JSONResponse(status_code=413, content={"detail": "Request body too large."})
                await response(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay_receive() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)


def _auth_dependency(expected_api_key: str | None) -> Callable[[str | None], None]:
    """Build the constant-time API-key dependency used by protected routes."""

    def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
        if not expected_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Set NEUDB_API_KEY before enabling the HTTP API.",
            )
        if not x_api_key or not hmac.compare_digest(x_api_key.encode("utf-8"), expected_api_key.encode("utf-8")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    return require_api_key


def _record_by_id(db: Database, table_name: str, record_id: str) -> dict:
    """Fetch a record by id or raise a 404."""
    record = db.table(table_name).get(record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record


def _validate_pagination(limit: int, offset: int) -> None:
    if limit < 1 or limit > 1000 or offset < 0:
        raise HTTPException(status_code=400, detail="limit must be 1-1000 and offset must be non-negative.")


def _cors_origins_from_env() -> list[str]:
    configured = os.environ.get("NEUDB_CORS_ORIGINS", "http://127.0.0.1:8080,http://localhost:8080")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def _max_request_bytes_from_env() -> int:
    raw = os.environ.get("NEUDB_MAX_REQUEST_BYTES", str(DEFAULT_MAX_REQUEST_BYTES))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError("NEUDB_MAX_REQUEST_BYTES must be an integer.") from exc
    if value < 1024:
        raise RuntimeError("NEUDB_MAX_REQUEST_BYTES must be at least 1024.")
    return value


def create_app(db_dir: str | None = None, api_key: str | None = None) -> FastAPI:
    """Create a FastAPI app backed by a neuDB directory."""
    db_path = db_dir or os.environ.get("NEUDB_API_DB", DEFAULT_API_DB_DIR)
    expected_api_key = api_key if api_key is not None else os.environ.get("NEUDB_API_KEY")
    max_request_bytes = _max_request_bytes_from_env()
    require_api_key = _auth_dependency(expected_api_key)
    db = ai_schema.init_ai_database(db_path)
    app = FastAPI(title="neuDB API", version=__version__)
    app.state.db = db
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins_from_env(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )
    app.add_middleware(RequestBodyLimitMiddleware, max_bytes=max_request_bytes)

    @app.exception_handler(CorruptedTableError)
    async def corrupted_table_handler(request: Request, exc: CorruptedTableError) -> JSONResponse:
        logger.error("Corrupted neuDB table at %s: %s", exc.path, exc)
        return JSONResponse(status_code=503, content={"detail": "Table data is corrupted."})

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(TypeError)
    async def type_error_handler(request: Request, exc: TypeError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(OSError)
    async def os_error_handler(request: Request, exc: OSError) -> JSONResponse:
        logger.error("neuDB storage error: %s", exc)
        return JSONResponse(status_code=503, content={"detail": "Storage is unavailable."})

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "auth_configured": bool(expected_api_key),
        }

    @app.get("/ready")
    def ready() -> dict[str, str]:
        if not expected_api_key:
            raise HTTPException(status_code=503, detail="API authentication is not configured.")
        if not db.db_dir.is_dir():
            raise HTTPException(status_code=503, detail="Storage is unavailable.")
        return {"status": "ready"}

    @app.get("/tables", dependencies=[Depends(require_api_key)])
    def list_tables() -> dict[str, list[str]]:
        return {"tables": db.list_tables()}

    @app.post("/tables", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
    def create_table(payload: TableCreate) -> dict[str, Any]:
        created = db.create_table(payload.name)
        return {"name": payload.name, "created": created}

    @app.get("/tables/{table_name}/records", dependencies=[Depends(require_api_key)])
    def list_records(table_name: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        _validate_pagination(limit, offset)
        records = db.table(table_name).select_all()
        return {"records": records[offset : offset + limit], "total": len(records)}

    @app.post(
        "/tables/{table_name}/records",
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_api_key)],
    )
    def insert_record(table_name: str, record: dict[str, Any]) -> dict[str, Any]:
        record_id = db.table(table_name).insert(record)
        return {"id": record_id, "record": _record_by_id(db, table_name, record_id)}

    @app.patch("/tables/{table_name}/records/{record_id}", dependencies=[Depends(require_api_key)])
    def update_record(
        table_name: str,
        record_id: Annotated[str, ApiPath(min_length=1, max_length=MAX_RECORD_ID_LENGTH)],
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        if not db.table(table_name).update(record_id, updates):
            raise HTTPException(status_code=404, detail="Record not found")
        return {"record": _record_by_id(db, table_name, record_id)}

    @app.delete("/tables/{table_name}/records/{record_id}", dependencies=[Depends(require_api_key)])
    def delete_record(
        table_name: str,
        record_id: Annotated[str, ApiPath(min_length=1, max_length=MAX_RECORD_ID_LENGTH)],
    ) -> dict[str, Any]:
        if not db.table(table_name).delete(record_id):
            raise HTTPException(status_code=404, detail="Record not found")
        return {"deleted": record_id}

    @app.post("/users", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
    def create_user(payload: UserCreate) -> dict[str, Any]:
        user_id = ai_schema.add_user(
            db,
            payload.username,
            payload.email,
            display_name=payload.display_name,
            metadata=payload.metadata,
        )
        return {"id": user_id, "user": _record_by_id(db, "users", user_id)}

    @app.post("/sessions", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
    def create_session(payload: SessionCreate) -> dict[str, Any]:
        session_id = ai_schema.create_session(
            db,
            payload.user_id,
            payload.title,
            description=payload.description,
            model=payload.model,
            metadata=payload.metadata,
        )
        return {"id": session_id, "session": _record_by_id(db, "sessions", session_id)}

    @app.post("/messages", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
    def create_message(payload: MessageCreate) -> dict[str, Any]:
        if payload.embedding is None:
            message_id = ai_schema.add_message_with_embedding(
                db,
                payload.session_id,
                payload.role,
                payload.content,
                metadata=payload.metadata,
            )
        else:
            message = {
                "session_id": payload.session_id,
                "role": payload.role,
                "content": payload.content,
                "metadata": payload.metadata,
            }
            message_id = db.table("messages").insert_with_embedding(message, payload.embedding)
        return {"id": message_id, "message": _record_by_id(db, "messages", message_id)}

    @app.get("/sessions/{session_id}/messages", dependencies=[Depends(require_api_key)])
    def list_session_messages(session_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        _validate_pagination(limit, offset)
        messages = ai_schema.get_session_messages(db, session_id)
        return {
            "messages": messages[offset : offset + limit],
            "total": len(messages),
        }

    @app.post("/search", dependencies=[Depends(require_api_key)])
    def search(payload: SearchRequest) -> dict[str, list[dict]]:
        if payload.vector is not None and payload.query is not None:
            raise HTTPException(status_code=400, detail="Provide exactly one of 'vector' or 'query'.")
        if payload.vector is not None:
            results = db.table(payload.table).search_similar(payload.field, payload.vector, top_k=payload.top_k)
        elif payload.query:
            query_vector = ai_schema.embed_text(payload.query)
            if query_vector is None:
                results = db.table(payload.table).search_text(payload.text_field, payload.query, top_k=payload.top_k)
            else:
                results = db.table(payload.table).search_similar(payload.field, query_vector, top_k=payload.top_k)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either 'vector' or 'query'.",
            )
        return {"results": results}

    return app


app = create_app()
