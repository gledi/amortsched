import datetime
import uuid

from pydantic import BaseModel


class UpsertProfileRequest(BaseModel):
    display_name: str | None = None
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str | None
    phone: str | None
    locale: str | None
    timezone: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
