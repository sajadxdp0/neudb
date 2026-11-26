"""Exceptions raised by neuDB."""

from pathlib import Path


class NeuDBError(Exception):
    """Base class for neuDB-specific errors."""


class CorruptedTableError(NeuDBError, ValueError):
    """Raised when a table file does not satisfy the neuDB table format.

    Subclasses :class:`ValueError` so existing ``except ValueError`` callers
    keep working. The offending path is available on ``.path``.
    """

    def __init__(self, path: Path, message: str):
        self.path = path
        super().__init__(f"{message}: {path}")
