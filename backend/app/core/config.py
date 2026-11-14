from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MewHelp"
    database_url: str = "postgresql://cao:cao@localhost:5432/cao"
    model_mode: Literal["demo", "openai"] = "demo"
    model_name: str = "gpt-4.1-mini"
    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = "https://api.openai.com/v1"
    model_timeout_seconds: float = Field(default=60, gt=0)
    embedding_model: str = "text-embedding-3-small"
    support_threshold: float = Field(default=0.38, ge=0, le=1)
    input_price_per_million: float | None = Field(default=None, ge=0)
    output_price_per_million: float | None = Field(default=None, ge=0)
    cookie_secure: bool = False
    session_hours: int = Field(default=24, ge=1, le=168)
    allow_registration: bool = True
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    @model_validator(mode="after")
    def validate_provider(self):
        if self.model_mode == "openai" and not self.openai_api_key.get_secret_value():
            raise ValueError("MODEL_MODE=openai 时必须配置 OPENAI_API_KEY")
        return self
