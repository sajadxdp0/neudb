"""Database directory management for neuDB."""

from pathlib import Path

from .config import _lock_for_path, validate_identifier
from .storage import write_table_file
from .table import Table


class Database:
    """A database is a folder containing table files."""

    def __init__(self, db_dir: str):
        self.db_dir = Path(db_dir).expanduser().resolve()

    def _table_path(self, name: str) -> Path:
        table_name = validate_identifier(name, "table name")
        path = (self.db_dir / f"{table_name}.json").resolve()
        if self.db_dir != path.parent:
            raise ValueError("Table path escapes database directory.")
        return path

    def table(self, name: str) -> Table:
        return Table(self._table_path(name))

    def list_tables(self) -> list[str]:
        """Return sorted, addressable table names directly inside this database."""
        if not self.db_dir.exists():
            return []
        names: list[str] = []
        for path in self.db_dir.glob("*.json"):
            if not path.is_file() or path.resolve().parent != self.db_dir:
                continue
            try:
                names.append(validate_identifier(path.stem, "table name"))
            except ValueError:
                continue
        return sorted(names)

    def create_table(self, name: str) -> bool:
        """Create an empty table and return True, or return False if it exists."""
        path = self._table_path(name)
        with _lock_for_path(path):
            if path.exists():
                return False
            path.parent.mkdir(parents=True, exist_ok=True)
            write_table_file(path, {})
        return True

    def drop_table(self, name: str) -> bool:
        """Delete a table file and return whether it existed."""
        path = self._table_path(name)
        with _lock_for_path(path):
            if not path.exists():
                return False
            path.unlink()
        return True


def connect(db_dir: str = "neudb_data") -> Database:
    """Connect to or create a database directory."""
    database = Database(db_dir)
    database.db_dir.mkdir(parents=True, exist_ok=True)
    return database
