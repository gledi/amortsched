import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from amortsched.api.schemas.auth import NewPassword, UserResponse
from amortsched.api.schemas.plans import PlanResponse
from amortsched.app.queries.users import AccountExport
from amortsched.core.entities import Profile


class UpsertProfileRequest(BaseModel):
    display_name: str | None = None
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str | None
    phone: str | None
    locale: str | None
    timezone: str | None
    currency: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @classmethod
    def from_entity(cls, profile: Profile) -> "ProfileResponse":
        return cls(
            id=profile.id,
            user_id=profile.user_id,
            display_name=profile.display_name,
            phone=profile.phone,
            locale=profile.locale,
            timezone=profile.timezone,
            currency=profile.currency,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )


class UpdateAccountRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: NewPassword


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class AccountExportResponse(BaseModel):
    exported_at: datetime.datetime
    user: UserResponse
    profile: ProfileResponse | None
    plans: list[PlanResponse]

    @classmethod
    def from_result(cls, result: AccountExport, exported_at: datetime.datetime) -> "AccountExportResponse":
        return cls(
            exported_at=exported_at,
            user=UserResponse.from_entity(result.user),
            profile=None if result.profile is None else ProfileResponse.from_entity(result.profile),
            plans=[PlanResponse.from_entity(plan) for plan in result.plans],
        )
