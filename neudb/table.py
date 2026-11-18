"""The table engine: one JSON file exposed as a record collection."""

import uuid
from pathlib import Path
from typing import Dict, List

from .config import _lock_for_path, validate_identifier
from .search import filter_by_text, rank_by_similarity
from .storage import (
    read_table_file,
    sweep_orphan_tmps as sweep_orphan_files,
    write_table_file,
)


class Table:
    """Represents a single table stored as a JSON file."""

    def __init__(self, path: str):
        self.path = Path(path)
        self._data: Dict[str, dict] = {}
        self._load()

    def sweep_orphan_tmps(self, max_age_seconds: float = 300) -> List[str]:
        """Remove stray temp files from interrupted `_save` calls.

        Explicit maintenance, never run on open: deleting a live temp file
        mid-write corrupts that write. Only old files are removed.
        """
        return sweep_orphan_files(self.path, max_age_seconds)

    def _read_file(self) -> Dict[str, dict]:
        return read_table_file(self.path)

    def _load(self) -> None:
        if self.path.exists():
            with _lock_for_path(self.path):
                self._data = self._read_file()

    def _reload(self) -> None:
        """Refresh this handle so multiple Table instances do not go stale."""
        if not self.path.exists():
            self._data = {}
            return
        with _lock_for_path(self.path):
            self._data = self._read_file()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _lock_for_path(self.path):
            write_table_file(self.path, self._data)

    def insert(self, record: dict) -> str:
        """Insert a record. If no 'id' field, auto-generate UUID."""
        if not isinstance(record, dict):
            raise TypeError("record must be a dictionary")
        with _lock_for_path(self.path):
            self._reload()
            record_id = record.get("id") or str(uuid.uuid4())
            record["id"] = record_id
            self._data[record_id] = record
            self._save()
            return record_id

    def insert_with_embedding(self, record: dict, embedding: List[float]) -> str:
        """Insert a record and attach an embedding vector."""
        record["embedding"] = embedding
        return self.insert(record)

    def select_all(self) -> List[dict]:
        self._reload()
        return list(self._data.values())

    def select_by(self, key: str, value: str) -> List[dict]:
        validate_identifier(key, "field name")
        self._reload()
        return [r for r in self._data.values() if str(r.get(key)) == value]

    def update(self, id: str, updates: dict) -> None:
        if not isinstance(updates, dict):
            raise TypeError("updates must be a dictionary")
        with _lock_for_path(self.path):
            self._reload()
            if id in self._data:
                self._data[id].update(updates)
                self._save()

    def delete(self, id: str) -> None:
        with _lock_for_path(self.path):
            self._reload()
            if id in self._data:
                del self._data[id]
                self._save()

    def exists(self, id: str) -> bool:
        self._reload()
        return id in self._data

    def search_similar(self, field: str, query_vector: List[float], top_k: int = 5) -> List[dict]:
        """Return top_k records sorted by cosine similarity of 'field' to query_vector."""
        validate_identifier(field, "field name")
        if top_k < 1:
            return []
        self._reload()
        return rank_by_similarity(self._data.values(), field, query_vector, top_k)

    def search_text(self, field: str, query: str, top_k: int = 5) -> List[dict]:
        """Return top_k records where field contains query, case-insensitive."""
        validate_identifier(field, "field name")
        if top_k < 1:
            return []
        self._reload()
        return filter_by_text(self._data.values(), field, query, top_k)
