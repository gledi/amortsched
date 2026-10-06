import pytest

from amortsched.api.cookies import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH


async def login(client, email: str, password: str = "testpass123"):
    return await client.post("/api/auth/token", data={"username": email, "password": password})


def refresh_cookie(client) -> str | None:
    return client.cookies.get(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def use_refresh_cookie(client, token: str) -> None:
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE_NAME, token, domain="testserver.local", path=REFRESH_COOKIE_PATH)


@pytest.mark.anyio
async def test_register_sets_httponly_refresh_cookie_and_sends_verification(client, outbox):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "User@Example.com", "name": "Test User", "password": "secret123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" not in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "user@example.com"
    assert data["user"]["email_verified"] is False

    set_cookie = resp.headers["set-cookie"]
    assert f"{REFRESH_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie
    assert f"Path={REFRESH_COOKIE_PATH}" in set_cookie

    assert [m.subject for m in outbox.messages] == ["Confirm your email address"]
    assert outbox.messages[0].to == "user@example.com"


@pytest.mark.anyio
async def test_login(client, register_user):
    await register_user(client, "login@example.com")
    client.cookies.clear()
    resp = await login(client, "login@example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" not in data
    assert refresh_cookie(client)


@pytest.mark.anyio
async def test_login_wrong_password(client, register_user):
    await register_user(client, "wrong@example.com")
    resp = await login(client, "wrong@example.com", "wrongpassword")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_is_rate_limited_per_email(client, register_user):
    await register_user(client, "limited@example.com")
    statuses = [(await login(client, "limited@example.com", "wrongpassword")).status_code for _ in range(11)]
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429

    resp = await login(client, "limited@example.com")
    assert resp.status_code == 429
    assert int(resp.headers["retry-after"]) > 0


@pytest.mark.anyio
async def test_duplicate_email(client, register_user):
    await register_user(client, "dup@example.com")
    resp = await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "name": "Another", "password": "pass1234"},
    )
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_refresh_rotates_cookie(client, register_user):
    await register_user(client, "refresh@example.com")
    original = refresh_cookie(client)

    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    rotated = refresh_cookie(client)
    assert rotated and rotated != original


@pytest.mark.anyio
async def test_refresh_without_cookie_is_unauthorized(client):
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_refresh_token_replay_revokes_family(client, register_user):
    await register_user(client, "replay@example.com")
    old_refresh = refresh_cookie(client)
    assert old_refresh

    assert (await client.post("/api/auth/refresh")).status_code == 200
    new_refresh = refresh_cookie(client)
    assert new_refresh

    use_refresh_cookie(client, old_refresh)
    assert (await client.post("/api/auth/refresh")).status_code == 401

    use_refresh_cookie(client, new_refresh)
    assert (await client.post("/api/auth/refresh")).status_code == 401


@pytest.mark.anyio
async def test_logout_revokes_and_clears_cookie(client, register_user):
    await register_user(client, "logout@example.com")
    refresh_token = refresh_cookie(client)
    assert refresh_token

    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 204
    assert refresh_cookie(client) is None

    use_refresh_cookie(client, refresh_token)
    assert (await client.post("/api/auth/refresh")).status_code == 401


@pytest.mark.anyio
async def test_refresh_with_invalid_token(client):
    use_refresh_cookie(client, "invalid-token")
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_registration_validates_identity_fields(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "name": "", "password": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_verify_email_with_emailed_token(client, outbox, auth_headers):
    token = outbox.last_token("test@example.com")

    resp = await client.post("/api/auth/verify-email", json={"token": token})
    assert resp.status_code == 200
    assert resp.json()["email_verified"] is True

    me = await client.get("/api/users/me", headers=auth_headers)
    assert me.json()["email_verified"] is True

    reused = await client.post("/api/auth/verify-email", json={"token": token})
    assert reused.status_code == 400


@pytest.mark.anyio
async def test_resending_verification_invalidates_previous_link(client, outbox, auth_headers):
    first = outbox.last_token("test@example.com")
    resp = await client.post("/api/users/me/verification-email", headers=auth_headers)
    assert resp.status_code == 202
    second = outbox.last_token("test@example.com")
    assert first != second

    assert (await client.post("/api/auth/verify-email", json={"token": first})).status_code == 400
    assert (await client.post("/api/auth/verify-email", json={"token": second})).status_code == 200


@pytest.mark.anyio
async def test_verify_email_rejects_password_reset_token(client, outbox, register_user):
    await register_user(client, "purpose@example.com")
    await client.post("/api/auth/password-reset/request", json={"email": "purpose@example.com"})
    reset_token = outbox.last_token("purpose@example.com")

    resp = await client.post("/api/auth/verify-email", json={"token": reset_token})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_password_reset_flow(client, outbox, register_user):
    await register_user(client, "reset@example.com")
    old_session = refresh_cookie(client)
    assert old_session

    resp = await client.post("/api/auth/password-reset/request", json={"email": "Reset@Example.com"})
    assert resp.status_code == 202
    assert outbox.messages[-1].subject == "Reset your password"
    token = outbox.last_token("reset@example.com")

    resp = await client.post("/api/auth/password-reset/confirm", json={"token": token, "password": "brand-new-pass"})
    assert resp.status_code == 204

    assert (await login(client, "reset@example.com")).status_code == 401
    assert (await login(client, "reset@example.com", "brand-new-pass")).status_code == 200

    use_refresh_cookie(client, old_session)
    assert (await client.post("/api/auth/refresh")).status_code == 401

    reused = await client.post("/api/auth/password-reset/confirm", json={"token": token, "password": "another-pass"})
    assert reused.status_code == 400


@pytest.mark.anyio
async def test_password_reset_for_unknown_email_is_silent(client, outbox):
    resp = await client.post("/api/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert resp.status_code == 202
    assert outbox.messages == []


@pytest.mark.anyio
async def test_password_reset_confirm_validates_password(client):
    resp = await client.post("/api/auth/password-reset/confirm", json={"token": "x", "password": "short"})
    assert resp.status_code == 422
