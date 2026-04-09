from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    secret_key: str = "amortsched-dev-secret-key-change-in-production"
    token_expiration_minutes: int = 30
    debug: bool = False
    refresh_token_expiration_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
