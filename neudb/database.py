"""Database directory management for neuDB."""

import os
from pathlib import Path
from typing import List

from .config import validate_identifier
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

    def list_tables(self) -> List[str]:
        """Return table names currently present in this database directory."""
        if not self.db_dir.exists():
            return []
        return sorted(path.stem for path in self.db_dir.glob("*.json") if path.is_file())

    def create_table(self, name: str) -> None:
        """Create a new table (just create an empty file)."""
        path = self._table_path(name)
        if not path.exists():
            table = Table(path)
            table._save()
            print(f"Table '{name}' created.")
        else:
            print(f"Table '{name}' already exists.")


def connect(db_dir: str = "neudb_data") -> Database:
    """Connect to (or create) a database directory."""
    os.makedirs(db_dir, exist_ok=True)
    return Database(db_dir)
