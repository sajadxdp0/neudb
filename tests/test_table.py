import pytest
from neudb import connect


def test_table_names_reject_path_traversal(tmp_path):
    db = connect(str(tmp_path))

    for name in ["../outside", "/tmp/outside", "bad-name", "nested/table"]:
        try:
            db.table(name)
        except ValueError as exc:
            assert "Invalid table name" in str(exc)
        else:
            raise AssertionError(f"table name should be rejected: {name}")


def test_create_table_rejects_path_traversal(tmp_path):
    db = connect(str(tmp_path))

    try:
        db.create_table("../outside")
    except ValueError as exc:
        assert "Invalid table name" in str(exc)
    else:
        raise AssertionError("create_table should reject path traversal")


def test_table_insert_select_update_delete(tmp_path):
    db = connect(str(tmp_path))
    users = db.table("users")

    user_id = users.insert({"username": "alice", "role": "admin"})

    assert users.exists(user_id)
    assert users.select_all() == [{"username": "alice", "role": "admin", "id": user_id}]
    assert users.select_by("username", "alice") == [{"username": "alice", "role": "admin", "id": user_id}]

    users.update(user_id, {"role": "owner"})

    assert users.select_by("role", "owner") == [{"username": "alice", "role": "owner", "id": user_id}]

    users.delete(user_id)

    assert users.select_all() == []
    assert not users.exists(user_id)


def test_table_persists_records_between_instances(tmp_path):
    db = connect(str(tmp_path))
    first_table = db.table("users")
    user_id = first_table.insert({"username": "bob"})

    second_table = db.table("users")

    assert second_table.select_all() == [{"username": "bob", "id": user_id}]


def test_table_handles_refresh_before_writes(tmp_path):
    db = connect(str(tmp_path))
    first_table = db.table("users")
    second_table = db.table("users")

    first_id = first_table.insert({"username": "first"})
    second_id = second_table.insert({"username": "second"})

    assert {record["id"] for record in first_table.select_all()} == {first_id, second_id}


def test_insert_does_not_mutate_input_and_generates_id_only_when_absent(tmp_path):
    table = connect(str(tmp_path)).table("users")
    record = {"username": "alice"}

    record_id = table.insert(record)

    assert "id" not in record
    assert table.get(record_id)["username"] == "alice"


@pytest.mark.parametrize("record_id", [None, "", 0, False, [], {}])
def test_insert_rejects_invalid_explicit_ids(tmp_path, record_id):
    table = connect(str(tmp_path)).table("users")

    with pytest.raises(ValueError, match="non-empty string"):
        table.insert({"id": record_id})


@pytest.mark.parametrize(
    "record",
    [
        {"value": {1, 2}},
        {"value": float("nan")},
        {"metadata": {1: "one"}},
        {"value": (1, 2)},
    ],
)
def test_insert_rejects_values_that_do_not_round_trip_through_json(tmp_path, record):
    table = connect(str(tmp_path)).table("users")

    with pytest.raises((TypeError, ValueError)):
        table.insert(record)


def test_update_and_delete_report_missing_records_and_ids_are_immutable(tmp_path):
    table = connect(str(tmp_path)).table("users")
    record_id = table.insert({"username": "alice"})

    assert table.update("missing", {"username": "nobody"}) is False
    assert table.delete("missing") is False
    with pytest.raises(ValueError, match="cannot be updated"):
        table.update(record_id, {"id": "replacement"})
    assert table.update(record_id, {"username": "alice-smith"}) is True
    assert table.delete(record_id) is True


def test_select_by_does_not_match_missing_fields(tmp_path):
    table = connect(str(tmp_path)).table("users")
    table.insert({"username": "alice"})

    assert table.select_by("missing", None) == []


def test_insert_many_is_atomic_when_batch_ids_are_duplicated(tmp_path):
    table = connect(str(tmp_path)).table("users")
    table.insert({"username": "existing"})

    with pytest.raises(ValueError, match="duplicate record IDs"):
        table.insert_many([{"id": "same"}, {"id": "same"}])

    assert table.count() == 1


def test_upsert_preserves_existing_id_and_unmentioned_fields(tmp_path):
    table = connect(str(tmp_path)).table("users")
    record_id = table.insert({"username": "alice", "role": "admin"})

    updated_id = table.upsert({"username": "alice", "role": "owner"}, ("username",))

    assert updated_id == record_id
    assert table.get(record_id) == {"id": record_id, "username": "alice", "role": "owner"}


def test_create_and_drop_table_return_status(tmp_path):
    db = connect(str(tmp_path))

    assert db.create_table("users") is True
    assert db.create_table("users") is False
    assert db.drop_table("users") is True
    assert db.drop_table("users") is False


def test_select_all_rejects_invalid_pagination(tmp_path):
    table = connect(str(tmp_path)).table("users")

    with pytest.raises(ValueError):
        table.select_all(offset=-1)
    with pytest.raises(ValueError):
        table.select_all(limit=0)


def test_insert_rejects_excessive_json_nesting(tmp_path):
    table = connect(str(tmp_path)).table("users")
    value = 0
    for _ in range(130):
        value = [value]

    with pytest.raises(ValueError, match="maximum nesting depth"):
        table.insert({"value": value})
