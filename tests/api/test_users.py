import pytest


@pytest.mark.anyio
async def test_user_cannot_access_or_modify_another_user(client, auth_headers):
    other = await client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "name": "Other User", "password": "testpass123"},
    )
    other_id = other.json()["user"]["id"]

    assert (await client.get(f"/api/users/{other_id}", headers=auth_headers)).status_code == 403
    assert (await client.get(f"/api/users/{other_id}/profile", headers=auth_headers)).status_code == 403
    assert (
        await client.put(
            f"/api/users/{other_id}/profile",
            json={"display_name": "Compromised"},
            headers=auth_headers,
        )
    ).status_code == 403


@pytest.mark.anyio
async def test_current_user_me_and_profile(client, auth_headers):
    me_resp = await client.get("/api/users/me", headers=auth_headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert "id" in me_data
    assert "email" in me_data

    # Update profile via /me/profile
    put_resp = await client.put(
        "/api/users/me/profile",
        json={"display_name": "My Name", "timezone": "UTC"},
        headers=auth_headers,
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["display_name"] == "My Name"

    # Read profile via /me/profile
    get_profile = await client.get("/api/users/me/profile", headers=auth_headers)
    assert get_profile.status_code == 200
    assert get_profile.json()["display_name"] == "My Name"
    assert get_profile.json()["timezone"] == "UTC"


@pytest.mark.anyio
async def test_profile_currency_is_normalized_and_validated(client, auth_headers):
    resp = await client.put("/api/users/me/profile", json={"currency": "eur"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["currency"] == "EUR"

    bad = await client.put("/api/users/me/profile", json={"currency": "E1R"}, headers=auth_headers)
    assert bad.status_code == 422


@pytest.mark.anyio
async def test_update_account_name(client, auth_headers):
    resp = await client.patch("/api/users/me", json={"name": "  Renamed  "}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"

    blank = await client.patch("/api/users/me", json={"name": "  "}, headers=auth_headers)
    assert blank.status_code == 422


@pytest.mark.anyio
async def test_change_password_revokes_other_sessions_and_keeps_current(client, auth_headers):
    other_device = await client.post(
        "/api/auth/token", data={"username": "test@example.com", "password": "testpass123"}
    )
    assert other_device.status_code == 200
    other_refresh = client.cookies.get("refresh_token", path="/api/auth")

    wrong = await client.post(
        "/api/users/me/password",
        json={"current_password": "nope", "new_password": "another-pass-1"},
        headers=auth_headers,
    )
    assert wrong.status_code == 403

    resp = await client.post(
        "/api/users/me/password",
        json={"current_password": "testpass123", "new_password": "another-pass-1"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    current_refresh = client.cookies.get("refresh_token", path="/api/auth")
    assert current_refresh and current_refresh != other_refresh

    assert (await client.post("/api/auth/refresh")).status_code == 200

    client.cookies.clear()
    client.cookies.set("refresh_token", other_refresh, domain="testserver.local", path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 401

    login = await client.post("/api/auth/token", data={"username": "test@example.com", "password": "another-pass-1"})
    assert login.status_code == 200


@pytest.mark.anyio
async def test_revoke_all_sessions(client, auth_headers):
    old_refresh = client.cookies.get("refresh_token", path="/api/auth")
    resp = await client.post("/api/users/me/sessions/revoke", headers=auth_headers)
    assert resp.status_code == 200
    assert client.cookies.get("refresh_token", path="/api/auth") != old_refresh
    assert (await client.post("/api/auth/refresh")).status_code == 200

    client.cookies.clear()
    client.cookies.set("refresh_token", old_refresh, domain="testserver.local", path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 401


@pytest.mark.anyio
async def test_export_account_data(client, auth_headers):
    await client.put("/api/users/me/profile", json={"currency": "GBP"}, headers=auth_headers)
    await client.post(
        "/api/plans",
        json={"name": "Home", "amount": "1000", "interest_rate": "1", "term": {"years": 1}},
        headers=auth_headers,
    )

    resp = await client.get("/api/users/me/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "attachment" in resp.headers["content-disposition"]
    data = resp.json()
    assert data["user"]["email"] == "test@example.com"
    assert data["profile"]["currency"] == "GBP"
    assert [plan["name"] for plan in data["plans"]] == ["Home"]
    assert "password_hash" not in str(data)


@pytest.mark.anyio
async def test_delete_account_requires_password_and_removes_everything(client, auth_headers):
    await client.post(
        "/api/plans",
        json={"name": "Home", "amount": "1000", "interest_rate": "1", "term": {"years": 1}},
        headers=auth_headers,
    )

    wrong = await client.request("DELETE", "/api/users/me", json={"password": "nope"}, headers=auth_headers)
    assert wrong.status_code == 403

    resp = await client.request("DELETE", "/api/users/me", json={"password": "testpass123"}, headers=auth_headers)
    assert resp.status_code == 204

    assert (await client.get("/api/users/me", headers=auth_headers)).status_code == 401
    login = await client.post("/api/auth/token", data={"username": "test@example.com", "password": "testpass123"})
    assert login.status_code == 401

    again = await client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "name": "Fresh", "password": "testpass123"},
    )
    assert again.status_code == 201
