import json

import pytest
from sqlalchemy import create_engine, text


async def call_asgi(app, method: str, path: str, body: dict, on_response_start) -> int:
    payload = json.dumps(body).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json"), (b"host", b"testserver")],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "state": {},
    }
    sent = False
    status = 0

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message):
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
            on_response_start()

    await app(scope, receive, send)
    return status


@pytest.mark.anyio
async def test_writes_are_committed_before_the_response_starts(client, database_url):
    app = client._transport.app
    engine = create_engine(database_url)
    seen_at_response_start: list[int] = []

    def count_users() -> None:
        with engine.connect() as connection:
            seen_at_response_start.append(connection.execute(text("SELECT count(*) FROM users")).scalar_one())

    try:
        status = await call_asgi(
            app,
            "POST",
            "/api/auth/register",
            {"email": "race@example.com", "name": "Race", "password": "testpass123"},
            count_users,
        )
    finally:
        engine.dispose()

    assert status == 201
    assert seen_at_response_start == [1]
