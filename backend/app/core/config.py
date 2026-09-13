from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FraudMesh XAI"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./fraudmesh.db"
    jwt_secret: str = "dev-access-secret-change-me-at-least-32-bytes"
    jwt_refresh_secret: str = "dev-refresh-secret-change-me-at-least-32-bytes"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    frontend_url: str = "http://localhost:5173"
    risk_medium_threshold: float = 0.45
    risk_high_threshold: float = 0.72
    risk_critical_threshold: float = 0.9
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    simulation_enabled: bool = True
    upload_max_bytes: int = 10_000_000
    demo_seed: bool = True
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str | None = None

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = value.replace("postgres://", "postgresql+asyncpg://", 1)
        elif value.startswith("postgresql://") and "+asyncpg" not in value:
            value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql+asyncpg://"):
            parsed = urlsplit(value)
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            ssl_mode = query.pop("sslmode", None)
            query.pop("channel_binding", None)
            if ssl_mode and "ssl" not in query:
                query["ssl"] = ssl_mode
            value = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
        return value

    cors_origins: list[str] = Field(default_factory=list)

    @property
    def allowed_origins(self) -> list[str]:
        return list(dict.fromkeys([self.frontend_url, "http://127.0.0.1:5173", *self.cors_origins]))

    @property
    def allowed_origin_regex(self) -> str | None:
        if self.environment.lower() == "development":
            return r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
