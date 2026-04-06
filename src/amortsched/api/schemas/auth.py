import uuid

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    is_active: bool


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
