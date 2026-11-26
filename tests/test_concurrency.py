import threading

import neudb.ai_schema as ai_schema
from neudb import connect, database


def test_concurrent_writes_lose_nothing(tmp_path):
    db = connect(str(tmp_path))
    threads, per_thread = 8, 25
    errors: list = []

    def worker(n: int):
        try:
            table = db.table("events")
            for i in range(per_thread):
                table.insert({"thread": n, "i": i})
        except Exception as exc:  # pragma: no cover — fail loudly below
            errors.append(exc)

    pool = [threading.Thread(target=worker, args=(n,)) for n in range(threads)]
    for t in pool:
        t.start()
    for t in pool:
        t.join()

    assert not errors, errors
    rows = db.table("events").select_all()
    assert len(rows) == threads * per_thread
    assert len({r["id"] for r in rows}) == threads * per_thread


def test_concurrent_readers_and_writers(tmp_path):
    """Reads reload from disk; they must never crash while a writer replaces the file."""
    import time

    db = connect(str(tmp_path))
    stop = threading.Event()
    errors: list = []

    def writer():
        table = db.table("mixed")
        i = 0
        while not stop.is_set():
            table.insert({"i": i})
            i += 1

    def reader():
        table = db.table("mixed")
        while not stop.is_set():
            try:
                table.select_all()
            except Exception as exc:
                errors.append(exc)
                return

    wt = threading.Thread(target=writer)
    readers = [threading.Thread(target=reader) for _ in range(4)]
    wt.start()
    for r in readers:
        r.start()
    time.sleep(0.5)
    stop.set()
    wt.join()
    for r in readers:
        r.join()
    assert not errors, errors


def test_create_table_does_not_overwrite_a_concurrent_insert(tmp_path, monkeypatch):
    db = connect(str(tmp_path))
    entered_write = threading.Event()
    release_write = threading.Event()
    errors = []

    real_write_table_file = database.write_table_file

    def delayed_write(path, data):
        if path.name == "users.json" and not data:
            entered_write.set()
            if not release_write.wait(5):
                raise TimeoutError("test did not release table creation")
        real_write_table_file(path, data)

    monkeypatch.setattr(database, "write_table_file", delayed_write)

    def create():
        try:
            db.create_table("users")
        except Exception as exc:
            errors.append(exc)

    def insert():
        try:
            db.table("users").insert({"username": "alice"})
        except Exception as exc:
            errors.append(exc)

    creator = threading.Thread(target=create)
    creator.start()
    assert entered_write.wait(5)
    inserter = threading.Thread(target=insert)
    inserter.start()
    release_write.set()
    creator.join(5)
    inserter.join(5)

    assert not errors, errors
    assert db.table("users").select_by("username", "alice")


def test_concurrent_tag_upserts_create_one_tag(tmp_path):
    db = ai_schema.init_ai_database(str(tmp_path))
    tag_ids = []
    errors = []

    def worker():
        try:
            tag_ids.append(ai_schema.add_tag(db, "python"))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, errors
    assert len(set(tag_ids)) == 1
    assert db.table("tags").count() == 1
