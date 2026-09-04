import pytest
from testcontainers.community.postgres import PostgresContainer


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:18-alpine") as pg:
        yield pg
