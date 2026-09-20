from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "dice-user-service"
    # Connects as user_service_role — least privilege, own schema only (see
    # infra/postgres/init/001_schemas_and_roles.sql and architecture doc §13.a).
    database_url: str = (
        "postgresql+psycopg://user_service_role:user_service_dev_pw"
        "@dice-postgres:5432/dice_job_manager"
    )
    jwt_private_key_path: str = "/app/secrets/jwt_private.pem"
    jwt_public_key_path: str = "/app/secrets/jwt_public.pem"
    jwt_algorithm: str = "RS256"
    jwt_access_token_minutes: int = 60
    # dice-test-client (Phase 4) runs as a plain Vite dev server, not in
    # Docker, so it's a different browser origin from every service it
    # calls — each service needs to explicitly allow it.
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
