from functools import lru_cache

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

    @property
    def token_expiration_minutes(self) -> int:
        return self.access_token_expiration // 60

    @property
    def refresh_token_expiration_days(self) -> int:
        return self.refresh_token_expiration // (24 * 3600)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    debug: bool = False

    security: SecuritySettings
    database: DatabaseSettings


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
