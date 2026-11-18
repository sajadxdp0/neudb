"""AI memory helpers for neuDB.

The embedding library is intentionally discovered and imported only when an
embedding is requested. This keeps the core API and dashboard fast to start.
"""

import importlib.util
from typing import Any, Dict, List, Optional

from . import connect
from .database import Database

SentenceTransformer: Any = None
EMBEDDING_AVAILABLE = importlib.util.find_spec("sentence_transformers") is not None
EMBED_MODEL: Any = None


def get_embedding_model() -> Any:
    """Load the embedding model on first use."""
    global EMBED_MODEL, SentenceTransformer
    if not EMBEDDING_AVAILABLE:
        return None
    if EMBED_MODEL is None:
        if SentenceTransformer is None:
            try:
                from sentence_transformers import SentenceTransformer as Transformer
            except ImportError:
                return None
            SentenceTransformer = Transformer
        EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return EMBED_MODEL


def embed_text(content: str) -> Optional[List[float]]:
    """Embed content, or return None when embeddings are unavailable."""
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
    display_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    user = {
        "username": username,
        "email": email,
        "display_name": display_name or username,
        "metadata": metadata or {},
    }
    return db.table("users").insert(user)


def create_session(
    db: Database,
    user_id: str,
    title: str,
    description: str = "",
    model: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    session = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "metadata": {"model": model, **(metadata or {})},
    }
    return db.table("sessions").insert(session)


def add_message(
    db: Database,
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    message = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }
    return db.table("messages").insert(message)


def add_message_with_embedding(
    db: Database,
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    message = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "embedding": embed_text(content),
        "metadata": metadata or {},
    }
    return db.table("messages").insert(message)


def add_tag(db: Database, name: str) -> str:
    """Return the existing tag id for name, or create a new tag."""
    tags = db.table("tags")
    existing = tags.select_by("name", name)
    if existing:
        return existing[0]["id"]
    return tags.insert({"name": name})


def tag_message(db: Database, message_id: str, tag_name: str) -> None:
    """Add tag_name to a message's metadata tags, creating the tag if needed."""
    add_tag(db, tag_name)
    messages = db.table("messages")
    records = messages.select_by("id", message_id)
    if records:
        record = records[0]
        tags = record.get("metadata", {}).get("tags", [])
        if tag_name not in tags:
            tags.append(tag_name)
            record["metadata"]["tags"] = tags
            messages.update(message_id, {"metadata": record["metadata"]})


def get_session_messages(db: Database, session_id: str) -> List[dict]:
    return [m for m in db.table("messages").select_all() if m["session_id"] == session_id]


def get_user_sessions(db: Database, user_id: str) -> List[dict]:
    return db.table("sessions").select_by("user_id", user_id)


def add_memory(
    db: Database,
    user_id: str,
    key: str,
    value: Any,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Upsert a key-value memory for a user and return its id."""
    memories = db.table("memories")
    for memory in memories.select_all():
        if memory["user_id"] == user_id and memory["key"] == key:
            memories.update(memory["id"], {"value": value, "metadata": metadata or {}})
            return memory["id"]
    return memories.insert({
        "user_id": user_id,
        "key": key,
        "value": value,
        "metadata": metadata or {},
    })


def get_memory(db: Database, user_id: str, key: str) -> Any:
    for memory in db.table("memories").select_all():
        if memory["user_id"] == user_id and memory["key"] == key:
            return memory["value"]
    return None
