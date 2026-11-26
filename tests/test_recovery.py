"""Recovery: corruption surfaces cleanly, interrupted writes can't half-apply."""

import pytest
from neudb import CorruptedTableError, connect


def test_corrupted_file_raises_corrupted_error(tmp_path):
    db = connect(str(tmp_path))
    users = db.table("users")
    users.insert({"username": "alice"})
    # Corrupt the file on disk.
    path = tmp_path / "users.json"
    path.write_text("{ not valid json !!!", encoding="utf-8")

    with pytest.raises(CorruptedTableError) as exc_info:
        db.table("users")
    assert str(tmp_path) in str(exc_info.value)


def test_non_object_json_rejected(tmp_path):
    (tmp_path / "users.json").write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(CorruptedTableError):
        connect(str(tmp_path)).table("users")


def test_interrupted_write_leaves_old_data_intact(tmp_path):
    """A stray .tmp file (crash between mkstemp and os.replace) never affects reads.

    Sweeping is explicit (Table.sweep_orphan_tmps), never on open: deleting
    temps on open would race live writers in other threads (see
    test_concurrency.py history). The table file itself is untouched by a crash.
    """
    import time

    db = connect(str(tmp_path))
    users = db.table("users")
    users.insert({"username": "alice"})
    # Simulate a crash: temp file exists, real file untouched.
    stray = tmp_path / ".users.json.abc123.tmp"
    stray.write_text('{"bogus": true}', encoding="utf-8")
    # Make it look old enough to be sweepable, then sweep explicitly.
    old = time.time() - 1000
    import os

    os.utime(stray, (old, old))

    reopened = db.table("users")  # must not crash, must not sweep live files
    assert reopened.select_by("username", "alice")
    assert stray.exists()  # opener leaves rebuttable debris alone
    removed = reopened.sweep_orphan_tmps()
    assert ".users.json.abc123.tmp" in removed
    assert not stray.exists()
    assert reopened.select_by("username", "alice")


def test_duplicate_ids_last_write_wins_explicitly(tmp_path):
    db = connect(str(tmp_path))
    t = db.table("docs")
    rid = t.insert({"id": "fixed", "v": 1})
    assert rid == "fixed"
    t.insert({"id": "fixed", "v": 2})
    assert t.select_all() == [{"id": "fixed", "v": 2}]


@pytest.mark.parametrize(
    "content",
    [
        '{"x": 42}',
        '{"x": {"username": "missing-id"}}',
        '{"x": {"id": "different"}}',
        '{"x": {"id": "x", "value": NaN}}',
    ],
)
def test_malformed_record_shape_is_reported_as_corruption(tmp_path, content):
    (tmp_path / "users.json").write_text(content, encoding="utf-8")

    with pytest.raises(CorruptedTableError):
        connect(str(tmp_path)).table("users")


def test_invalid_utf8_is_reported_as_corruption(tmp_path):
    (tmp_path / "users.json").write_bytes(b"\xff\xfe")

    with pytest.raises(CorruptedTableError):
        connect(str(tmp_path)).table("users")


@pytest.mark.parametrize("max_age", [float("nan"), float("inf"), -1])
def test_sweep_rejects_invalid_max_age(tmp_path, max_age):
    table = connect(str(tmp_path)).table("users")

    with pytest.raises(ValueError, match="finite non-negative"):
        table.sweep_orphan_tmps(max_age)


def test_failed_replace_preserves_old_file_and_cleans_temp(tmp_path, monkeypatch):
    db = connect(str(tmp_path))
    table = db.table("users")
    record_id = table.insert({"username": "alice"})

    def fail_replace(source, destination):
        raise OSError("injected replace failure")

    monkeypatch.setattr("neudb.storage.os.replace", fail_replace)

    with pytest.raises(OSError, match="injected replace failure"):
        table.insert({"username": "bob"})

    assert table.get(record_id) == {"id": record_id, "username": "alice"}
    assert list(tmp_path.glob(".users.json.*.tmp")) == []
