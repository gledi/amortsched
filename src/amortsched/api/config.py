from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    dsn: PostgresDsn

    @property
    def url(self) -> str:
        return self.dsn.unicode_string()


class SecuritySettings(BaseModel):
    secret_key: str

    access_token_expiration: int = 300  # in seconds
    refresh_token_expiration: int = 7 * 24 * 3600  # in seconds
    cookie_secure: bool = True

    @property
    def token_expiration_minutes(self) -> int:
        return self.access_token_expiration // 60

    @property
    def refresh_token_expiration_days(self) -> int:
        return self.refresh_token_expiration // (24 * 3600)


class EmailSettings(BaseModel):
    backend: Literal["console", "smtp"] = "console"
    sender: str = "Amortsched <no-reply@localhost>"
    host: str = "localhost"
    port: int = 1025
    username: str | None = None
    password: str | None = None
    starttls: bool = False
    use_ssl: bool = False


class RateLimitSettings(BaseModel):
    backend: Literal["memory", "redis"] = "memory"
    redis_url: str = "redis://localhost:6379/0"
    enabled: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(  # pyright: ignore[reportUnannotatedClassAttribute]
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    debug: bool = False
    public_url: str = "http://localhost:3000"

    security: SecuritySettings
    database: DatabaseSettings
    email: EmailSettings = EmailSettings()
    rate_limit: RateLimitSettings = RateLimitSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
