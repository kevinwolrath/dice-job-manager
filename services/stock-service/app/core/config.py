from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "dice-stock-service"
    # Connects as stock_service_role — least privilege, owns its own schema
    # (infra/postgres/init/001_schemas_and_roles.sql, architecture doc §13.a).
    database_url: str = (
        "postgresql+psycopg://stock_service_role:stock_service_dev_pw"
        "@dice-postgres:5432/dice_job_manager"
    )
    jwt_public_key_path: str = "/app/secrets/jwt_public.pem"
    jwt_algorithm: str = "RS256"
    # dice-test-client (Phase 4) runs as a plain Vite dev server, not in
    # Docker, so it's a different browser origin from every service it
    # calls — each service needs to explicitly allow it.
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
