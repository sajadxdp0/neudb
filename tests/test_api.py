import neudb.ai_schema as ai_schema
from fastapi.testclient import TestClient
from neudb.api import create_app

API_KEY = "test-api-key"
AUTH_HEADERS = {"X-API-Key": API_KEY}


def test_api_rejects_missing_api_key(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    response = client.post("/users", json={"username": "alice", "email": "alice@example.com"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key."


def test_api_user_session_message_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_schema, "EMBEDDING_AVAILABLE", False)
    monkeypatch.setattr(ai_schema, "EMBED_MODEL", None)
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    user_response = client.post(
        "/users",
        headers=AUTH_HEADERS,
        json={"username": "alice", "email": "alice@example.com", "display_name": "Alice"},
    )
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    session_response = client.post(
        "/sessions",
        headers=AUTH_HEADERS,
        json={"user_id": user_id, "title": "Debugging", "model": "codellama"},
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]

    message_response = client.post(
        "/messages",
        headers=AUTH_HEADERS,
        json={"session_id": session_id, "role": "user", "content": "How do I fix imports?"},
    )
    assert message_response.status_code == 201
    assert message_response.json()["message"]["embedding"] is None

    messages_response = client.get(f"/sessions/{session_id}/messages", headers=AUTH_HEADERS)
    assert messages_response.status_code == 200
    messages = messages_response.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["content"] == "How do I fix imports?"


def test_api_search_with_vector(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_schema, "EMBEDDING_AVAILABLE", False)
    monkeypatch.setattr(ai_schema, "EMBED_MODEL", None)
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    first = client.post(
        "/messages",
        headers=AUTH_HEADERS,
        json={"session_id": "s1", "role": "user", "content": "Python", "embedding": [1.0, 0.0]},
    )
    second = client.post(
        "/messages",
        headers=AUTH_HEADERS,
        json={"session_id": "s1", "role": "user", "content": "Weather", "embedding": [0.0, 1.0]},
    )

    response = client.post("/search", headers=AUTH_HEADERS, json={"vector": [1.0, 0.0], "top_k": 1})

    assert response.status_code == 200
    assert response.json()["results"] == [first.json()["message"]]
    assert second.json()["message"] not in response.json()["results"]


def test_api_search_requires_query_or_vector(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    response = client.post("/search", headers=AUTH_HEADERS, json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide either 'vector' or 'query'."


def test_api_search_falls_back_to_text_when_embeddings_are_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_schema, "embed_text", lambda content: None)
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))
    matching = client.post(
        "/messages",
        headers=AUTH_HEADERS,
        json={"session_id": "s1", "role": "user", "content": "Python import help"},
    )
    client.post(
        "/messages",
        headers=AUTH_HEADERS,
        json={"session_id": "s1", "role": "user", "content": "Weather report"},
    )

    response = client.post("/search", headers=AUTH_HEADERS, json={"query": "python", "top_k": 5})

    assert response.status_code == 200
    assert response.json()["results"] == [matching.json()["message"]]


def test_api_dashboard_table_and_record_crud(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    create_table = client.post("/tables", headers=AUTH_HEADERS, json={"name": "notes"})
    assert create_table.status_code == 201
    assert "notes" in client.get("/tables", headers=AUTH_HEADERS).json()["tables"]

    created = client.post("/tables/notes/records", headers=AUTH_HEADERS, json={"title": "hello"})
    assert created.status_code == 201
    record_id = created.json()["id"]

    updated = client.patch(f"/tables/notes/records/{record_id}", headers=AUTH_HEADERS, json={"title": "updated"})
    assert updated.status_code == 200
    assert updated.json()["record"]["title"] == "updated"

    listed = client.get("/tables/notes/records", headers=AUTH_HEADERS).json()
    assert listed["total"] == 1
    assert listed["records"][0]["title"] == "updated"

    deleted = client.delete(f"/tables/notes/records/{record_id}", headers=AUTH_HEADERS)
    assert deleted.status_code == 200
    assert client.get("/tables/notes/records", headers=AUTH_HEADERS).json()["total"] == 0


def test_api_invalid_table_name_returns_422(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    response = client.get("/tables/bad-name/records", headers=AUTH_HEADERS)

    assert response.status_code == 422
    assert "Invalid table name" in response.json()["detail"]


def test_api_empty_key_is_reported_as_unconfigured(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=""))

    assert client.get("/health").json()["auth_configured"] is False
    assert client.get("/tables").status_code == 503


def test_api_search_rejects_both_query_and_vector(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    response = client.post("/search", headers=AUTH_HEADERS, json={"query": "python", "vector": [1.0, 0.0]})

    assert response.status_code == 400


def test_api_rejects_id_updates_and_missing_records(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))
    created = client.post("/tables/notes/records", headers=AUTH_HEADERS, json={"title": "hello"}).json()
    record_id = created["id"]

    immutable = client.patch(f"/tables/notes/records/{record_id}", headers=AUTH_HEADERS, json={"id": "new-id"})
    missing = client.patch("/tables/notes/records/missing", headers=AUTH_HEADERS, json={"title": "updated"})

    assert immutable.status_code == 422
    assert missing.status_code == 404


def test_api_rejects_oversized_request_bodies(tmp_path, monkeypatch):
    monkeypatch.setenv("NEUDB_MAX_REQUEST_BYTES", "1024")
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    response = client.post("/tables/notes/records", headers=AUTH_HEADERS, json={"content": "x" * 2048})

    assert response.status_code == 413


def test_api_reports_corrupted_tables_as_unavailable(tmp_path):
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))
    (tmp_path / "messages.json").write_text('{"broken": 1}', encoding="utf-8")

    response = client.get("/tables/messages/records", headers=AUTH_HEADERS)

    assert response.status_code == 503
    assert response.json()["detail"] == "Table data is corrupted."


def test_api_ready_fails_closed_without_auth(tmp_path):
    configured = TestClient(create_app(str(tmp_path / "configured"), api_key=API_KEY))
    unconfigured = TestClient(create_app(str(tmp_path / "unconfigured"), api_key=""))

    assert configured.get("/ready").status_code == 200
    assert unconfigured.get("/ready").status_code == 503


def test_api_rejects_oversized_chunked_request(tmp_path, monkeypatch):
    monkeypatch.setenv("NEUDB_MAX_REQUEST_BYTES", "1024")
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))

    def chunks():
        yield b'{"content":"'
        yield b"x" * 2048
        yield b'"}'

    response = client.post(
        "/tables/notes/records",
        headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        content=chunks(),
    )

    assert response.status_code == 413


def test_api_session_messages_are_paginated(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_schema, "EMBEDDING_AVAILABLE", False)
    client = TestClient(create_app(str(tmp_path), api_key=API_KEY))
    for content in ["first", "second", "third"]:
        client.post(
            "/messages",
            headers=AUTH_HEADERS,
            json={"session_id": "s1", "role": "user", "content": content},
        )

    response = client.get("/sessions/s1/messages?limit=1&offset=1", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert [message["content"] for message in response.json()["messages"]] == ["second"]
