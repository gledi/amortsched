import uuid

import pytest
from amortsched.app.users.upsert_profile import UpsertProfileCommand, UpsertProfileHandler
from amortsched.core.entities import User
from amortsched.core.errors import UserNotFoundError


@pytest.fixture
def handler(profile_repo, user_repo):
    return UpsertProfileHandler(profile_repo, user_repo)


@pytest.fixture
def sample_user(user_repo):
    user = User(email="alice@example.com", name="Alice", password_hash="hashed")
    user_repo.add(user)
    return user


def test_upsert_profile_creates(handler, sample_user, profile_repo):
    command = UpsertProfileCommand(
        user_id=sample_user.id,
        display_name="Alice W.",
        phone="+355123456",
        locale="en-US",
        timezone="America/New_York",
    )
    profile = handler.handle(command)
    assert profile.user_id == sample_user.id
    assert profile.display_name == "Alice W."
    assert profile.phone == "+355123456"
    assert profile.locale == "en-US"
    assert profile.timezone == "America/New_York"
    assert profile_repo.get_by_id(profile.id) is profile


def test_upsert_profile_updates_existing(handler, sample_user, profile_repo):
    cmd1 = UpsertProfileCommand(user_id=sample_user.id, display_name="Alice")
    profile = handler.handle(cmd1)
    original_id = profile.id

    cmd2 = UpsertProfileCommand(user_id=sample_user.id, display_name="Alice Updated", locale="sq-AL")
    updated = handler.handle(cmd2)
    assert updated.id == original_id
    assert updated.display_name == "Alice Updated"
    assert updated.locale == "sq-AL"
    assert profile_repo.count() == 1


def test_upsert_profile_user_not_found(handler):
    command = UpsertProfileCommand(user_id=uuid.uuid7(), display_name="Nobody")
    with pytest.raises(UserNotFoundError):
        handler.handle(command)
