import uuid

import pytest
from amortsched.app.users.get_profile import GetProfileHandler, GetProfileQuery
from amortsched.core.entities import Profile, User
from amortsched.core.errors import ProfileNotFoundError


@pytest.fixture
def handler(profile_repo):
    return GetProfileHandler(profile_repo)


@pytest.fixture
def sample_user(user_repo):
    user = User(email="alice@example.com", name="Alice", password_hash="hashed")
    user_repo.add(user)
    return user


@pytest.fixture
def sample_profile(profile_repo, sample_user):
    profile = Profile(user_id=sample_user.id, display_name="Alice W.")
    profile_repo.add(profile)
    return profile


def test_get_profile(handler, sample_profile, sample_user):
    query = GetProfileQuery(user_id=sample_user.id)
    fetched = handler.handle(query)
    assert fetched.id == sample_profile.id
    assert fetched.display_name == "Alice W."


def test_get_profile_not_found(handler):
    query = GetProfileQuery(user_id=uuid.uuid7())
    with pytest.raises(ProfileNotFoundError):
        handler.handle(query)
