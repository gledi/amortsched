import pytest
from amortsched.app.users.register import RegisterUserCommand, RegisterUserHandler


@pytest.fixture
def handler(user_repo, password_hasher):
    return RegisterUserHandler(user_repo, password_hasher)


def test_register_creates_user(handler):
    command = RegisterUserCommand(email="bob@example.com", name="Bob", password="pw123")
    user = handler.handle(command)
    assert user.email == "bob@example.com"
    assert user.name == "Bob"


def test_register_hashes_password(handler):
    command = RegisterUserCommand(email="bob@example.com", name="Bob", password="pw123")
    user = handler.handle(command)
    assert user.password_hash != "pw123"
    assert user.password_hash != ""


def test_register_persists_user(handler, user_repo):
    command = RegisterUserCommand(email="bob@example.com", name="Bob", password="pw123")
    user = handler.handle(command)
    fetched = user_repo.get_by_id(user.id)
    assert fetched is user
