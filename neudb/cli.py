"""Command-line interface for neuDB."""

import json
import sys
from typing import List, Optional

from .database import Database, connect


def _option_value(argv: List[str], option: str) -> Optional[str]:
    """Return the argument following option, or None when the option is absent."""
    if option not in argv:
        return None
    return argv[argv.index(option) + 1]


def _handle_table(db: Database, action: str, name: str) -> None:
    if action == "create":
        db.create_table(name)
    else:
        print("Unknown table action. Use 'create'.")


def _handle_row(db: Database, action: str, table_name: str, argv: List[str]) -> None:
    table = db.table(table_name)

    if action == "insert":
        data_str = _option_value(argv, "--data")
        if data_str is None:
            print("Use --data '<json>'")
            return
        record = json.loads(data_str)
        record_id = table.insert(record)
        print(f"Inserted with ID: {record_id}")

    elif action == "list":
        for row in table.select_all():
            print(row)

    elif action == "find":
        condition = _option_value(argv, "--where")
        if condition is None:
            print("Use --where key=value")
            return
        if "=" in condition:
            key, value = condition.split("=", 1)
            for row in table.select_by(key.strip(), value.strip()):
                print(row)
        else:
            print("Format: --where key=value")

    elif action == "delete":
        record_id = _option_value(argv, "--id")
        if record_id is None:
            print("Use --id <id>")
            return
        table.delete(record_id)
        print(f"Deleted {record_id}")

    elif action == "search":
        if "--field" in argv and "--vector" in argv:
            field_name = _option_value(argv, "--field")
            vec_str = _option_value(argv, "--vector")
            query_vector = json.loads(vec_str)
            for row in table.search_similar(field_name, query_vector):
                print(row)
        else:
            print("Usage: row search <table> --field <field_name> --vector '[0.1,0.2,...]'")

    else:
        print("Unknown row action. Use: insert, list, find, delete, search.")


def main() -> None:
    """Run the neuDB CLI using ``sys.argv``."""
    argv = sys.argv
    if len(argv) < 2:
        # Imported lazily: the usage text is the public package docstring.
        from . import __doc__ as usage

        print(usage)
        return

    command = argv[1]
    db = connect()

    if command == "table" and len(argv) >= 4:
        _handle_table(db, argv[2], argv[3])
    elif command == "row":
        if len(argv) < 4:
            print("Usage: row <action> <table> [options]")
            return
        _handle_row(db, argv[2], argv[3], argv)
    else:
        print("Unknown command. Use 'table' or 'row'.")


if __name__ == "__main__":
    main()
