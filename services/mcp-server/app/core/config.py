from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "dice-mcp-server"

    # dice-mcp-server owns no database and issues no tokens — it verifies
    # the caller's JWT the same independent way every other service does
    # (architecture doc §11), then forwards that same token, unchanged, to
    # whichever backend service a tool needs to call. There is no user_id
    # anywhere in this service's own code; the calling human's identity is
    # entirely carried by the bearer token it's handed.
    jwt_public_key_path: str = "/app/secrets/jwt_public.pem"
    jwt_algorithm: str = "RS256"

    # Docker-network-internal URLs — this service never talks to the other
    # services through the host-published ports, only over the compose
    # network.
    job_service_url: str = "http://dice-job-service:4103"
    stock_service_url: str = "http://dice-stock-service:4102"
    user_service_url: str = "http://dice-user-service:4101"
    ollama_url: str = "http://dice-ollama:11434"
    ollama_model: str = "llama3.1:8b"

    # dice-test-client (Phase 4/6) is the only browser caller of this
    # service (its chat panel), same as the other three services.
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
