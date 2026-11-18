"""Exceptions raised by neuDB."""

from pathlib import Path


class CorruptedTableError(ValueError):
    """Raised when a table file exists but is not valid JSON.

    Subclasses ValueError so existing `except ValueError` callers keep working,
    while new code can catch the specific case and decide (restore from backup,
    quarantine the file, abort). The offending path is on `.path`.
    """

    def __init__(self, path: Path, message: str):
        self.path = path
        super().__init__(f"{message}: {path}")
