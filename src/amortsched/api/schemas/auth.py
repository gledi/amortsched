import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from amortsched.core.entities import User

type NewPassword = Annotated[str, Field(min_length=8, max_length=1024)]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    password: NewPassword


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    is_active: bool
    email_verified: bool

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            email_verified=user.email_verified,
        )


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    password: NewPassword
