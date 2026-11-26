"""Command-line interface for neuDB."""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from typing import Any

from ._version import __version__
from .database import connect


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _json_object(value: str, label: str) -> dict:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return parsed


def _json_vector(value: str) -> list[float]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError("--vector must be a JSON array of finite numbers.")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neudb",
        description="Inspectable embedded JSON storage with text and vector search.",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("NEUDB_DB", "neudb_data"),
        help="database directory (default: NEUDB_DB or ./neudb_data)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--version", action="version", version=f"neuDB {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    tables = commands.add_parser("table", help="manage tables")
    table_actions = tables.add_subparsers(dest="action", required=True)
    table_create = table_actions.add_parser("create", help="create an empty table")
    table_create.add_argument("name")
    table_actions.add_parser("list", help="list tables")
    table_drop = table_actions.add_parser("drop", help="permanently delete a table")
    table_drop.add_argument("name")
    table_drop.add_argument("--yes", action="store_true", help="confirm deletion")

    rows = commands.add_parser("row", help="manage records")
    row_actions = rows.add_subparsers(dest="action", required=True)

    row_insert = row_actions.add_parser("insert", help="insert a record")
    row_insert.add_argument("table")
    row_insert.add_argument("--data", required=True, help="record as a JSON object")

    row_list = row_actions.add_parser("list", help="list records as JSON Lines")
    row_list.add_argument("table")
    row_list.add_argument("--limit", type=_positive_int)
    row_list.add_argument("--offset", type=_nonnegative_int, default=0)

    row_get = row_actions.add_parser("get", help="print one record")
    row_get.add_argument("table")
    row_get.add_argument("--id", required=True)

    row_find = row_actions.add_parser("find", help="find records by field equality")
    row_find.add_argument("table")
    row_find.add_argument("--where", required=True, help="field=value")
    row_find.add_argument("--limit", type=_positive_int)
    row_find.add_argument("--offset", type=_nonnegative_int, default=0)

    row_update = row_actions.add_parser("update", help="merge fields into a record")
    row_update.add_argument("table")
    row_update.add_argument("--id", required=True)
    row_update.add_argument("--data", required=True, help="updates as a JSON object")

    row_delete = row_actions.add_parser("delete", help="delete a record")
    row_delete.add_argument("table")
    row_delete.add_argument("--id", required=True)

    row_search = row_actions.add_parser("search", help="rank records by cosine similarity")
    row_search.add_argument("table")
    row_search.add_argument("--field", required=True)
    row_search.add_argument("--vector", required=True, help="query vector as a JSON array")
    row_search.add_argument("--top-k", type=_positive_int, default=5)

    row_search_text = row_actions.add_parser("search-text", help="case-insensitive substring search")
    row_search_text.add_argument("table")
    row_search_text.add_argument("--field", required=True)
    row_search_text.add_argument("--query", required=True)
    row_search_text.add_argument("--top-k", type=_positive_int, default=5)

    return parser


def _emit(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, ensure_ascii=False))
    elif isinstance(value, list):
        for item in value:
            print(json.dumps(item, ensure_ascii=False))
    else:
        print(value)


def _handle_table(args: argparse.Namespace) -> None:
    db = connect(args.db)
    if args.action == "list":
        _emit(db.list_tables(), args.json)
        return
    if args.action == "create":
        created = db.create_table(args.name)
        if args.json:
            _emit({"name": args.name, "created": created}, True)
        else:
            print(f"Table '{args.name}' {'created' if created else 'already exists'}.")
        return
    if not args.yes:
        raise ValueError("table drop requires --yes.")
    deleted = db.drop_table(args.name)
    if args.json:
        _emit({"name": args.name, "deleted": deleted}, True)
    else:
        print(f"Table '{args.name}' {'deleted' if deleted else 'does not exist'}.")


def _handle_row(args: argparse.Namespace) -> None:
    table = connect(args.db).table(args.table)
    if args.action == "insert":
        record = _json_object(args.data, "--data")
        record_id = table.insert(record)
        _emit({"id": record_id, "record": table.get(record_id)}, args.json)
        if not args.json:
            print(f"Inserted with ID: {record_id}")
        return
    if args.action == "list":
        records = table.select_all(limit=args.limit, offset=args.offset)
        _emit(records, args.json)
        return
    if args.action == "get":
        fetched_record = table.get(args.id)
        if fetched_record is None:
            raise ValueError(f"Record not found: {args.id}")
        _emit(fetched_record, args.json)
        return
    if args.action == "find":
        if "=" not in args.where:
            raise ValueError("--where must use field=value.")
        key, value = args.where.split("=", 1)
        records = table.select_by(key.strip(), value.strip())
        records = records[args.offset :] if args.limit is None else records[args.offset : args.offset + args.limit]
        _emit(records, args.json)
        return
    if args.action == "update":
        updates = _json_object(args.data, "--data")
        if not table.update(args.id, updates):
            raise ValueError(f"Record not found: {args.id}")
        _emit(table.get(args.id), args.json)
        return
    if args.action == "delete":
        if not table.delete(args.id):
            raise ValueError(f"Record not found: {args.id}")
        _emit({"id": args.id, "deleted": True}, args.json)
        return
    if args.action == "search":
        records = table.search_similar(args.field, _json_vector(args.vector), top_k=args.top_k)
        _emit(records, args.json)
        return
    if args.action == "search-text":
        records = table.search_text(args.field, args.query, top_k=args.top_k)
        _emit(records, args.json)
        return
    raise ValueError(f"Unknown row action: {args.action}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the neuDB CLI and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "table":
            _handle_table(args)
        else:
            _handle_row(args)
    except (OSError, TypeError, ValueError) as exc:
        print(f"neudb: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
