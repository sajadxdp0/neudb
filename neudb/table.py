"""The table engine: one JSON file exposed as a record collection."""

import uuid
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from .config import _lock_for_path, validate_identifier
from .search import filter_by_text, rank_by_similarity, validate_vector
from .storage import (
    read_table_file,
    validate_json_value,
    validate_record,
    validate_record_id,
    write_table_file,
)
from .storage import (
    sweep_orphan_tmps as sweep_orphan_files,
)


def _prepare_record(record: dict) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TypeError("record must be a dictionary")
    prepared = dict(record)
    if "id" not in prepared:
        prepared["id"] = str(uuid.uuid4())
    validate_record(prepared)
    return prepared


class Table:
    """A record collection stored as one JSON object on disk."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data: dict[str, dict] = {}
        self._load()

    def sweep_orphan_tmps(self, max_age_seconds: float = 300) -> list[str]:
        """Remove old temp files while excluding same-process writers."""
        with _lock_for_path(self.path):
            return sweep_orphan_files(self.path, max_age_seconds)

    def _read_file(self) -> dict[str, dict]:
        return read_table_file(self.path)

    def _load(self) -> None:
        self._reload()

    def _reload(self) -> None:
        """Refresh this handle while excluding same-process writers."""
        with _lock_for_path(self.path):
            self._data = self._read_file() if self.path.exists() else {}

    def _write(self, data: dict[str, dict]) -> None:
        """Commit a complete snapshot, then publish it to this handle."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _lock_for_path(self.path):
            write_table_file(self.path, data)
            self._data = data

    def insert(self, record: dict) -> str:
        """Insert a record and return its ID.

        The caller's dictionary is not modified. Supplying an existing ID
        intentionally replaces that record (last write wins).
        """
        prepared = _prepare_record(record)
        record_id = prepared["id"]
        with _lock_for_path(self.path):
            self._reload()
            data = dict(self._data)
            data[record_id] = prepared
            self._write(data)
        return record_id

    def insert_many(self, records: Iterable[dict]) -> list[str]:
        """Insert a batch in one atomic write and return IDs in input order."""
        prepared_records = [_prepare_record(record) for record in records]
        record_ids = [record["id"] for record in prepared_records]
        if not prepared_records:
            return []
        if len(set(record_ids)) != len(record_ids):
            raise ValueError("Batch contains duplicate record IDs.")
        with _lock_for_path(self.path):
            self._reload()
            data = dict(self._data)
            for record in prepared_records:
                data[record["id"]] = record
            self._write(data)
        return record_ids

    def upsert(self, record: dict, keys: Sequence[str]) -> str:
        """Insert or merge a record matched by one or more unique fields.

        Matching and replacement happen under the same path lock. Existing
        IDs and fields not present in ``record`` are preserved.
        """
        if not isinstance(record, dict):
            raise TypeError("record must be a dictionary")
        if isinstance(keys, (str, bytes)) or not keys:
            raise ValueError("upsert requires at least one key field.")
        for key in keys:
            validate_identifier(key, "upsert key")
            if key not in record:
                raise ValueError(f"Upsert record is missing key field {key!r}.")
        validate_json_value(record, "record")
        if "id" in record:
            validate_record_id(record["id"])

        with _lock_for_path(self.path):
            self._reload()
            data = dict(self._data)
            for existing in self._data.values():
                if all(key in existing and existing[key] == record[key] for key in keys):
                    record_id = existing["id"]
                    merged = {**existing, **record, "id": record_id}
                    validate_record(merged)
                    data[record_id] = merged
                    self._write(data)
                    return record_id
            prepared = _prepare_record(record)
            record_id = prepared["id"]
            data[record_id] = prepared
            self._write(data)
        return record_id

    def insert_with_embedding(self, record: dict, embedding: list[float]) -> str:
        """Insert a record with an embedding without mutating the input."""
        if not isinstance(record, dict):
            raise TypeError("record must be a dictionary")
        validate_vector(embedding, "embedding")
        return self.insert({**record, "embedding": embedding})

    def get(self, id: str) -> dict | None:
        """Return a copy of one record, or None when it does not exist."""
        validate_record_id(id)
        with _lock_for_path(self.path):
            self._reload()
            record = self._data.get(id)
            return dict(record) if record is not None else None

    def select_all(self, limit: int | None = None, offset: int = 0) -> list[dict]:
        """Return record copies, optionally sliced by ``offset`` and ``limit``."""
        if offset < 0 or (limit is not None and limit < 1):
            raise ValueError("offset must be non-negative and limit must be positive.")
        with _lock_for_path(self.path):
            self._reload()
            records = list(self._data.values())
        sliced = records[offset:] if limit is None else records[offset : offset + limit]
        return [dict(record) for record in sliced]

    def select_by(self, key: str, value: Any) -> list[dict]:
        """Return records whose field equals ``value`` using JSON equality."""
        validate_identifier(key, "field name")
        with _lock_for_path(self.path):
            self._reload()
            return [dict(record) for record in self._data.values() if key in record and record[key] == value]

    def update(self, id: str, updates: dict) -> bool:
        """Merge fields into a record and return whether it existed.

        Record IDs are immutable. A failed validation or write leaves both the
        file and this handle unchanged.
        """
        validate_record_id(id)
        if not isinstance(updates, dict):
            raise TypeError("updates must be a dictionary")
        if "id" in updates:
            raise ValueError("Record IDs cannot be updated.")
        validate_json_value(updates, "updates")
        with _lock_for_path(self.path):
            self._reload()
            if id not in self._data:
                return False
            record = {**self._data[id], **updates}
            validate_record(record)
            data = dict(self._data)
            data[id] = record
            self._write(data)
        return True

    def delete(self, id: str) -> bool:
        """Delete a record and return whether it existed."""
        validate_record_id(id)
        with _lock_for_path(self.path):
            self._reload()
            if id not in self._data:
                return False
            data = dict(self._data)
            del data[id]
            self._write(data)
        return True

    def exists(self, id: str) -> bool:
        validate_record_id(id)
        with _lock_for_path(self.path):
            self._reload()
            return id in self._data

    def count(self) -> int:
        with _lock_for_path(self.path):
            self._reload()
            return len(self._data)

    def search_similar(self, field: str, query_vector: list[float], top_k: int = 5) -> list[dict]:
        """Return up to ``top_k`` records ordered by cosine similarity."""
        validate_identifier(field, "field name")
        if top_k < 1:
            return []
        with _lock_for_path(self.path):
            self._reload()
            matches = rank_by_similarity(self._data.values(), field, query_vector, top_k)
        return [dict(record) for record in matches]

    def search_text(self, field: str, query: str, top_k: int = 5) -> list[dict]:
        """Return records whose field contains ``query``, case-insensitively."""
        validate_identifier(field, "field name")
        if top_k < 1:
            return []
        with _lock_for_path(self.path):
            self._reload()
            matches = filter_by_text(self._data.values(), field, query, top_k)
        return [dict(record) for record in matches]
