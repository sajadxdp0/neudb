"""Shared identifier validation and process-local path locking."""

import re
import threading
import weakref
from pathlib import Path
from typing import Any

IDENTIFIER_PATTERN = r"^[A-Za-z0-9_]+$"
MAX_IDENTIFIER_LENGTH = 128

_IDENTIFIER_RE = re.compile(IDENTIFIER_PATTERN)
_PATH_LOCKS: "weakref.WeakValueDictionary[str, Any]" = weakref.WeakValueDictionary()
_PATH_LOCKS_GUARD = threading.Lock()


def validate_identifier(value: str, label: str = "identifier") -> str:
    """Validate a table or field identifier.

    Identifiers contain only ASCII letters, numbers, and underscores and are
    limited to 128 characters so they are safe in paths, URLs, and logs.
    """
    if not isinstance(value, str) or len(value) > MAX_IDENTIFIER_LENGTH or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Invalid {label}: use 1-{MAX_IDENTIFIER_LENGTH} letters, numbers, and underscores.")
    return value


def _lock_for_path(path: Path) -> Any:
    """Return the process-local reentrant lock that guards a table path.

    The weak value dictionary avoids retaining one lock forever for every
    path a long-running process has ever opened.
    """
    key = str(path.resolve())
    with _PATH_LOCKS_GUARD:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _PATH_LOCKS[key] = lock
        return lock
