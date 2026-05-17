from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parents[2]
ENV_FILE_PATH = BASE_DIR / ".env"


class AppSettings(BaseSettings):
    """Describes config for app settings."""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=ENV_FILE_PATH,
        extra="ignore",
    )

    title: str = "FastAPI Service"

    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    reload: bool = False


class APIPrefixes(BaseSettings):
    """Describes prefixes for API."""

    model_config = SettingsConfigDict(
        env_prefix="PREFIX_",
        env_file=ENV_FILE_PATH,
        extra="ignore",
    )

    public: str = "/public"
    admin: str = "/admin"


class PostgreSQL(BaseSettings):
    """Describes PostgreSQL DSN in preferred format."""

    model_config = SettingsConfigDict(
        env_prefix="POSTGRESQL_",
        env_file=ENV_FILE_PATH,
        extra="ignore",
    )

    dsn: str = "postgresql+asyncpg://user:password@127.0.0.1:5432/db"

    def build_using_new_scheme(self, scheme: str) -> str:
        return "://".join([scheme, self.dsn.split("://")[1]])

    @property
    def using_sync_driver(self) -> str:
        return self.build_using_new_scheme(scheme="postgresql+psycopg2")

    @property
    def using_async_driver(self) -> str:
        return self.build_using_new_scheme(scheme="postgresql+asyncpg")

    @property
    def using_async_driver_for_test(self) -> str:
        split_new_scheme = self.build_using_new_scheme(
            scheme="postgresql+asyncpg"
        ).split("/")
        return "/".join(
            split_new_scheme[:-1] + [f"test_{split_new_scheme[-1]}"]
        )


class Security(BaseSettings):
    """Describes settings for security reasons."""

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=ENV_FILE_PATH,
        extra="ignore",
    )

    api_key: str = "secret_key"


class Config(BaseSettings):
    """Describes application config."""

    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, extra="ignore")

    app: AppSettings
    prefixes: APIPrefixes
    postgresql: PostgreSQL
    security: Security

    @classmethod
    def create(cls) -> "Config":
        return Config(
            app=AppSettings(),
            prefixes=APIPrefixes(),
            postgresql=PostgreSQL(),
            security=Security(),
        )
