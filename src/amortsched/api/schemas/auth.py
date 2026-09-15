import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=1024)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    is_active: bool


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
