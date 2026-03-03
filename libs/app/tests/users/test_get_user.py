import uuid

import pytest
from amortsched.app.users.get_user import GetUserHandler, GetUserQuery
from amortsched.app.users.register import RegisterUserCommand, RegisterUserHandler
from amortsched.core.errors import UserNotFoundError


@pytest.fixture
def register_handler(user_repo, password_hasher):
    return RegisterUserHandler(user_repo, password_hasher)


@pytest.fixture
def handler(user_repo):
    return GetUserHandler(user_repo)


@pytest.fixture
def existing_user(register_handler):
    return register_handler.handle(RegisterUserCommand(email="alice@example.com", name="Alice", password="s3cret!"))


def test_get_user_returns_user(handler, existing_user):
    query = GetUserQuery(user_id=existing_user.id)
    fetched = handler.handle(query)
    assert fetched.email == existing_user.email


def test_get_user_not_found_raises(handler):
    query = GetUserQuery(user_id=uuid.uuid7())
    with pytest.raises(UserNotFoundError):
        handler.handle(query)
