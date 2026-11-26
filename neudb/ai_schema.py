"""AI memory helpers for neuDB.

The embedding library is discovered and imported only when an embedding is
requested, keeping the core package fast to start.
"""

import importlib.util
import threading
from datetime import UTC, datetime
from typing import Any

from .database import Database, connect

SentenceTransformer: Any = None
EMBEDDING_AVAILABLE = importlib.util.find_spec("sentence_transformers") is not None
EMBED_MODEL: Any = None
_EMBEDDING_LOCK = threading.Lock()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def get_embedding_model() -> Any:
    """Load the embedding model once, on first use."""
    global EMBED_MODEL, SentenceTransformer
    if not EMBEDDING_AVAILABLE:
        return None
    if EMBED_MODEL is None:
        with _EMBEDDING_LOCK:
            if EMBED_MODEL is None:
                if SentenceTransformer is None:
                    try:
                        from sentence_transformers import SentenceTransformer as Transformer
                    except ImportError:
                        return None
                    SentenceTransformer = Transformer
                EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return EMBED_MODEL


def embed_text(content: str) -> list[float] | None:
    """Embed content, or return None when embeddings are unavailable."""
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    model = get_embedding_model()
    if model is None:
        return None
    return model.encode(content).tolist()


def init_ai_database(db_dir: str = "ai_memory") -> Database:
    """Connect to db_dir and ensure the standard AI tables exist."""
    db = connect(db_dir)
    for name in ["users", "sessions", "messages", "tags", "memories"]:
        db.create_table(name)
    return db


def add_user(
    db: Database,
    username: str,
    email: str,
    display_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    user = {
        "username": username,
        "email": email,
        "display_name": display_name or username,
        "metadata": dict(metadata or {}),
        "created_at": _utc_now(),
    }
    return db.table("users").insert(user)


def create_session(
    db: Database,
    user_id: str,
    title: str,
    description: str = "",
    model: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    session = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "metadata": {"model": model, **dict(metadata or {})},
        "created_at": _utc_now(),
    }
    return db.table("sessions").insert(session)


def _message_record(
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None,
    with_embedding: bool,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": dict(metadata or {}),
        "created_at": _utc_now(),
    }
    if with_embedding:
        message["embedding"] = embed_text(content)
    return message


def add_message(
    db: Database,
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    return db.table("messages").insert(_message_record(session_id, role, content, metadata, False))


def add_message_with_embedding(
    db: Database,
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    return db.table("messages").insert(_message_record(session_id, role, content, metadata, True))


def add_exchange(
    db: Database,
    session_id: str,
    user_content: str,
    assistant_content: str,
    user_metadata: dict[str, Any] | None = None,
    assistant_metadata: dict[str, Any] | None = None,
) -> list[str]:
    """Persist a user/assistant exchange in one atomic table write."""
    records = [
        _message_record(session_id, "user", user_content, user_metadata, True),
        _message_record(session_id, "assistant", assistant_content, assistant_metadata, True),
    ]
    return db.table("messages").insert_many(records)


def add_tag(db: Database, name: str) -> str:
    """Return the existing tag ID for name, or atomically create it."""
    return db.table("tags").upsert({"name": name}, ("name",))


def tag_message(db: Database, message_id: str, tag_name: str) -> None:
    """Add tag_name to a message's metadata tags, creating the tag if needed."""
    messages = db.table("messages")
    record = messages.get(message_id)
    if record is None:
        return
    add_tag(db, tag_name)
    metadata = dict(record.get("metadata") or {})
    tags = list(metadata.get("tags") or [])
    if tag_name not in tags:
        tags.append(tag_name)
        metadata["tags"] = tags
        messages.update(message_id, {"metadata": metadata})


def get_session_messages(db: Database, session_id: str) -> list[dict]:
    return [message for message in db.table("messages").select_all() if message.get("session_id") == session_id]


def get_user_sessions(db: Database, user_id: str) -> list[dict]:
    return db.table("sessions").select_by("user_id", user_id)


def get_user_messages(db: Database, user_id: str) -> list[dict]:
    """Return messages across every session owned by one user."""
    session_ids = {session["id"] for session in get_user_sessions(db, user_id)}
    return [message for message in db.table("messages").select_all() if message.get("session_id") in session_ids]


def add_memory(
    db: Database,
    user_id: str,
    key: str,
    value: Any,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Atomically upsert a key-value memory for a user and return its ID."""
    return db.table("memories").upsert(
        {
            "user_id": user_id,
            "key": key,
            "value": value,
            "metadata": dict(metadata or {}),
        },
        ("user_id", "key"),
    )


def get_memory(db: Database, user_id: str, key: str) -> Any:
    for memory in db.table("memories").select_all():
        if memory.get("user_id") == user_id and memory.get("key") == key:
            return memory.get("value")
    return None
