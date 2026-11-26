import json

import pytest
from neudb import main


def test_cli_table_and_record_round_trip(tmp_path, capsys):
    database = str(tmp_path)
    prefix = ["--db", database, "--json"]

    assert main([*prefix, "table", "create", "users"]) == 0
    assert json.loads(capsys.readouterr().out) == {"name": "users", "created": True}

    assert main([*prefix, "row", "insert", "users", "--data", '{"username":"alice"}']) == 0
    created = json.loads(capsys.readouterr().out)
    record_id = created["id"]

    assert main([*prefix, "row", "list", "users"]) == 0
    assert json.loads(capsys.readouterr().out) == [created["record"]]

    assert main([*prefix, "row", "get", "users", "--id", record_id]) == 0
    assert json.loads(capsys.readouterr().out) == created["record"]

    assert main([*prefix, "row", "find", "users", "--where", "username=alice"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 1

    assert main([*prefix, "row", "update", "users", "--id", record_id, "--data", '{"role":"admin"}']) == 0
    assert json.loads(capsys.readouterr().out)["role"] == "admin"

    assert main([*prefix, "row", "search-text", "users", "--field", "username", "--query", "ALI"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 1

    assert main([*prefix, "row", "delete", "users", "--id", record_id]) == 0
    assert json.loads(capsys.readouterr().out) == {"id": record_id, "deleted": True}


def test_cli_errors_return_nonzero_and_do_not_modify_data(tmp_path, capsys):
    database = str(tmp_path)

    assert main(["--db", database, "table", "create", "users"]) == 0
    capsys.readouterr()
    assert main(["--db", database, "row", "insert", "users", "--data", "not-json"]) == 1
    assert "neudb: error:" in capsys.readouterr().err

    assert main(["--db", database, "row", "get", "users", "--id", "missing"]) == 1
    assert "Record not found" in capsys.readouterr().err


def test_cli_drop_requires_explicit_confirmation(tmp_path, capsys):
    database = str(tmp_path)
    assert main(["--db", database, "table", "create", "users"]) == 0
    capsys.readouterr()

    assert main(["--db", database, "table", "drop", "users"]) == 1
    assert "--yes" in capsys.readouterr().err
    assert main(["--db", database, "table", "drop", "users", "--yes"]) == 0
    assert "deleted" in capsys.readouterr().out


def test_cli_missing_required_option_uses_argparse_exit_code(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        main(["--db", str(tmp_path), "row", "insert", "users"])

    assert exc_info.value.code == 2
