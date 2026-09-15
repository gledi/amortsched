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
