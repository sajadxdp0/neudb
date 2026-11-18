"""JSON file I/O for tables: validated reads and atomic writes."""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List

from .errors import CorruptedTableError


def read_table_file(path: Path) -> Dict[str, dict]:
    """Load a table file, raising CorruptedTableError for invalid content."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise CorruptedTableError(
            path, f"table file is not valid JSON ({exc})"
        ) from exc
    except UnicodeDecodeError as exc:
        raise CorruptedTableError(
            path, f"table file is not valid UTF-8 ({exc})"
        ) from exc
    if not isinstance(data, dict):
        raise CorruptedTableError(
            path, f"table file must contain a JSON object, got {type(data).__name__}"
        )
    return data


def write_table_file(path: Path, data: Dict[str, dict]) -> None:
    """Atomically replace a table file using a temp file, fsync and os.replace.

    The caller holds the path lock; the parent directory must already exist.
    """
    temp_path = None
    fd, temp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def sweep_orphan_tmps(path: Path, max_age_seconds: float = 300) -> List[str]:
    """Remove stale temp files left by interrupted writes; return basenames.

    This is explicit maintenance, deliberately NOT run on open: a concurrent
    writer in another thread/process may have a live temp file with the same
    pattern, and deleting it mid-write corrupts that write. Only files older
    than max_age_seconds are removed.
    """
    removed: List[str] = []
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
