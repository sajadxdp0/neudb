"""JSON file I/O for tables: validated reads and durable atomic writes."""

import errno
import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from .errors import CorruptedTableError

MAX_JSON_DEPTH = 128


def _validate_json_value(value: Any, label: str, active: set[int], depth: int) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ValueError(f"{label} exceeds the maximum nesting depth of {MAX_JSON_DEPTH}.")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{label} must not contain NaN or infinity.")
        return
    if isinstance(value, (list, dict)):
        marker = id(value)
        if marker in active:
            raise ValueError(f"{label} must not contain circular references.")
        active.add(marker)
        try:
            if isinstance(value, list):
                for index, item in enumerate(value):
                    _validate_json_value(item, f"{label}[{index}]", active, depth + 1)
            else:
                for key, item in value.items():
                    if not isinstance(key, str):
                        raise TypeError(f"{label} object keys must be strings.")
                    _validate_json_value(item, f"{label}.{key}", active, depth + 1)
        finally:
            active.remove(marker)
        return
    raise TypeError(f"{label} must contain only JSON-compatible values.")


def validate_json_value(value: Any, label: str = "value") -> None:
    """Reject values that cannot round-trip through strict JSON."""
    _validate_json_value(value, label, set(), 0)


def validate_record_id(value: Any, label: str = "record ID") -> str:
    """Validate a record identifier without imposing identifier syntax."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string.")
    return value


def validate_record(record: Any) -> None:
    """Validate the JSON value and ID invariant for one record."""
    if not isinstance(record, dict):
        raise TypeError("record must be a dictionary")
    validate_json_value(record, "record")
    validate_record_id(record.get("id"))


def _validate_table_data(data: dict[str, dict]) -> None:
    if not isinstance(data, dict):
        raise TypeError("table data must be a dictionary")
    for record_id, record in data.items():
        validate_record_id(record_id, "table key")
        validate_record(record)
        if record["id"] != record_id:
            raise ValueError(f"Record ID {record['id']!r} does not match table key {record_id!r}.")


def read_table_file(path: Path) -> dict[str, dict]:
    """Load a table file, raising CorruptedTableError for invalid content."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise CorruptedTableError(path, f"table file is not valid JSON ({exc})") from exc
    except UnicodeDecodeError as exc:
        raise CorruptedTableError(path, f"table file is not valid UTF-8 ({exc})") from exc
    except RecursionError as exc:
        raise CorruptedTableError(path, "table file exceeds the maximum nesting depth") from exc
    if not isinstance(data, dict):
        raise CorruptedTableError(path, f"table file must contain a JSON object, got {type(data).__name__}")
    try:
        _validate_table_data(data)
    except (TypeError, ValueError) as exc:
        raise CorruptedTableError(path, str(exc)) from exc
    return data


def _fsync_directory(directory: Path) -> None:
    """Persist a rename on POSIX filesystems that support directory fsync."""
    if os.name != "posix":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(directory, flags)
    except OSError:
        return
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.EBADF}:
                raise
    finally:
        os.close(fd)


def write_table_file(path: Path, data: dict[str, dict]) -> None:
    """Atomically and durably replace a table file.

    The caller holds the path lock and has created the parent directory. The
    temporary file is flushed and fsynced before ``os.replace``; supporting
    POSIX filesystems then fsync the parent directory to persist the rename.
    """
    _validate_table_data(data)
    fd, temp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
        _fsync_directory(path.parent)
    finally:
        temp_path.unlink(missing_ok=True)


def sweep_orphan_tmps(path: Path, max_age_seconds: float = 300) -> list[str]:
    """Remove stale temp files left by interrupted writes; return basenames.

    This is explicit maintenance, deliberately NOT run on open: a concurrent
    writer may have a live temp file with the same pattern. Only files older
    than ``max_age_seconds`` are removed.
    """
    try:
        valid_age = math.isfinite(max_age_seconds) and max_age_seconds >= 0
    except TypeError:
        valid_age = False
    if not valid_age:
        raise ValueError("max_age_seconds must be a finite non-negative number.")
    removed: list[str] = []
    try:
        parent = path.parent
        if not parent.exists():
            return removed
        now = time.time()
        for tmp in parent.glob(f".{path.name}.*.tmp"):
            try:
                if now - tmp.stat().st_mtime < max_age_seconds:
                    continue
                tmp.unlink()
                removed.append(tmp.name)
            except OSError:
                pass
    except OSError:
        pass
    return removed
