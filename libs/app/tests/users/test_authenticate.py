import pytest
from amortsched.app.users.authenticate import AuthenticateUserCommand, AuthenticateUserHandler
from amortsched.app.users.register import RegisterUserCommand, RegisterUserHandler
from amortsched.core.errors import AuthenticationError


@pytest.fixture
def register_handler(user_repo, password_hasher):
    return RegisterUserHandler(user_repo, password_hasher)


@pytest.fixture
def handler(user_repo, password_hasher):
    return AuthenticateUserHandler(user_repo, password_hasher)


@pytest.fixture
def registered_user(register_handler):
    return register_handler.handle(RegisterUserCommand(email="bob@example.com", name="Bob", password="pw123"))


def test_authenticate_success(handler, registered_user):
    command = AuthenticateUserCommand(email="bob@example.com", password="pw123")
    user = handler.handle(command)
    assert user.email == "bob@example.com"


def test_authenticate_wrong_password(handler, registered_user):
    command = AuthenticateUserCommand(email="bob@example.com", password="wrong")
    with pytest.raises(AuthenticationError):
        handler.handle(command)


def test_authenticate_unknown_email(handler):
    command = AuthenticateUserCommand(email="nobody@example.com", password="pw")
    with pytest.raises(AuthenticationError):
        handler.handle(command)
