#!/usr/bin/env python3
"""
neuDB - lightweight embedded Python storage experiment (zero dependencies).

One JSON file per table ({id: record}), atomic writes via temp + fsync +
os.replace, per-path threading.RLock (same process only), brute-force text +
cosine search. NOT a server, index, or PostgreSQL replacement.

Usage as CLI:
  python neudb.py table create <name>
  python neudb.py row insert <table> --data '<json>'
  python neudb.py row list <table>
  python neudb.py row find <table> --where <key=value>
  python neudb.py row search <table> --field embedding --vector '[0.1,0.2,...]'

Usage as library:
  import neudb
  db = neudb.connect("mydata")
  users = db.table("users")
  users.insert({"username": "alice"})
  users.insert({"text": "hello", "embedding": [0.1, 0.2]})
  results = users.search_similar("embedding", [0.1, 0.2])
"""

from .cli import main
from .config import validate_identifier
from .database import Database, connect
from .errors import CorruptedTableError
from .search import cosine_similarity
from .table import Table

__all__ = [
    "CorruptedTableError",
    "Database",
    "Table",
    "connect",
    "cosine_similarity",
    "main",
    "validate_identifier",
]


if __name__ == "__main__":
    main()
