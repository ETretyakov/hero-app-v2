from pathlib import Path

from pydantic import BaseSettings, PostgresDsn


BASE_DIR = Path(__file__).parents[2]
ENV_FILE_PATH = BASE_DIR / ".env"


class AppSettings(BaseSettings):
    """Describes config for app settings."""

    class Config:
        env_prefix: str = "APP_"
        env_file: str = ENV_FILE_PATH

    title: str = "FastAPI Service"

    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    reload: bool = False


class APIPrefixes(BaseSettings):
    """Describes prefixes for API."""

    class Config:
        env_prefix: str = "PREFIX_"
        env_file: str = ENV_FILE_PATH

    public: str = "/public"
    admin: str = "/admin"


class PostgreSQL(BaseSettings):
    """Describes PostgreSQL DSN in preferred format."""

    __separator = "://"

    class Config:
        env_prefix: str = "POSTGRESQL_"
        env_file: str = ENV_FILE_PATH

    dsn: PostgresDsn = "postgres://user:password@127.0.0.1:5432/db"

    def build_using_new_scheme(self, scheme: str) -> str:
        return f"{self.__separator}".join(
            [scheme, self.dsn.split(sep=self.__separator)[1]],
        )

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

    class Config:
        env_prefix: str = "SECURITY_"
        env_file: str = ENV_FILE_PATH

    api_key: str = "secret_key"


class Config(BaseSettings):
    """Describes application config."""

    class Config:
        env_file: str = ENV_FILE_PATH

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
