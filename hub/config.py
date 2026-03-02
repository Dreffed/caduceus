from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Hub
    # Empty string disables API key enforcement
    hub_api_key: str = Field(default="")
    hub_debug: bool = False
    hub_log_level: str = "INFO"
    hub_version: str = "1.0.0"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Google OAuth2
    google_client_id: str = ""
    google_client_secret: str = ""
    google_token_file: str = "/data/google_token.json"

    # Weather (Open-Meteo — no key required)
    open_meteo_latitude: float = 49.2827
    open_meteo_longitude: float = -123.1207
    open_meteo_timezone: str = "America/Vancouver"
    open_meteo_location_name: str = "Vancouver, BC"

    # Email (IMAP)
    imap_host: str = ""
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""

    # Hexoplan
    hexoplan_api_key: str = ""
    hexoplan_base_url: str = "https://api.hexoplan.com"

    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434"


@lru_cache
def get_settings() -> Settings:
    return Settings()
