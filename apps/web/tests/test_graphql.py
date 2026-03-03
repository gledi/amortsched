"""GraphQL endpoint tests for FastAPI web app."""

import pytest

pytestmark = pytest.mark.anyio


async def _graphql(client, query, variables=None, headers=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    return await client.post("/graphql", json=payload, headers=headers or {})


async def test_register_mutation(client):
    query = """
    mutation { register(input: {email: "gql@e.com", name: "GQL", password: "pass"}) {
        user { id email name } token
    }}
    """
    resp = await _graphql(client, query)
    assert resp.status_code == 200
    data = resp.json()["data"]["register"]
    assert data["user"]["email"] == "gql@e.com"
    assert data["token"]


async def test_login_mutation(client):
    # First register
    await _graphql(
        client,
        'mutation { register(input: {email: "gql2@e.com", name: "U", password: "p"}) { token } }',
    )
    resp = await _graphql(
        client,
        'mutation { login(input: {email: "gql2@e.com", password: "p"}) { token } }',
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["login"]["token"]


async def test_me_query(client, register_user):
    token = await register_user(client, "gqlme@e.com")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await _graphql(client, "{ me { id email name isActive } }", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["me"]["email"] == "gqlme@e.com"


async def test_create_and_list_plans(client, register_user):
    token = await register_user(client, "gqlplan@e.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_query = """
    mutation { createPlan(input: {
        name: "GQL Plan", amount: "100000", interestRate: "5.0",
        termYears: 10, termMonths: 0, startDate: "2026-01-15"
    }) { id name status } }
    """
    resp = await _graphql(client, create_query, headers=headers)
    assert resp.status_code == 200
    plan = resp.json()["data"]["createPlan"]
    assert plan["name"] == "GQL Plan"

    resp = await _graphql(client, "{ plans { id name } }", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]["plans"]) >= 1


async def test_preview_schedule_mutation(client, register_user):
    token = await register_user(client, "gqlsched@e.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await _graphql(
        client,
        """mutation { createPlan(input: {
            name: "Sched Plan", amount: "50000", interestRate: "4.0",
            termYears: 5, startDate: "2026-01-15"
        }) { id } }""",
        headers=headers,
    )
    plan_id = create_resp.json()["data"]["createPlan"]["id"]

    query = (
        f'mutation {{ previewSchedule(planId: "{plan_id}")'
        " { id installments { year month } totals { months } } }"
    )
    resp = await _graphql(client, query, headers=headers)
    assert resp.status_code == 200
    schedule = resp.json()["data"]["previewSchedule"]
    assert len(schedule["installments"]) > 0


async def test_unauthenticated_query_returns_error(client):
    resp = await _graphql(client, "{ me { id } }")
    assert resp.status_code == 200  # GraphQL always 200
    assert resp.json().get("errors") is not None
