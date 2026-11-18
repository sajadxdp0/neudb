"""Shared identifier validation and process-local path locking."""

import re
import threading
from pathlib import Path
from typing import Any, Dict

IDENTIFIER_PATTERN = r"^[A-Za-z0-9_]+$"

_IDENTIFIER_RE = re.compile(IDENTIFIER_PATTERN)
_PATH_LOCKS: Dict[str, Any] = {}
_PATH_LOCKS_GUARD = threading.Lock()


def validate_identifier(value: str, label: str = "identifier") -> str:
    """Validate a table or field identifier used to build paths/query records."""
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Invalid {label}: use only letters, numbers, and underscores.")
    return value


def _lock_for_path(path: Path) -> Any:
    """Return the process-local reentrant lock that guards a table path."""
    key = str(path.resolve())
    with _PATH_LOCKS_GUARD:
        if key not in _PATH_LOCKS:
            _PATH_LOCKS[key] = threading.RLock()
        return _PATH_LOCKS[key]
