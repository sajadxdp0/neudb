"""neuDB — inspectable embedded Python storage.

A database is a directory; a table is one UTF-8 JSON object mapping record IDs
to records. The core uses only the Python standard library and provides
atomic writes, process-local thread safety, text search, and cosine similarity.
It is intended for local tools, prototypes, and LLM-agent memory, not as a
server database or a PostgreSQL replacement.
"""

from ._version import __version__
from .cli import main
from .config import validate_identifier
from .database import Database, connect
from .errors import CorruptedTableError, NeuDBError
from .search import cosine_similarity
from .table import Table

__all__ = [
    "CorruptedTableError",
    "Database",
    "NeuDBError",
    "Table",
    "__version__",
    "connect",
    "cosine_similarity",
    "main",
    "validate_identifier",
]


if __name__ == "__main__":
    raise SystemExit(main())
