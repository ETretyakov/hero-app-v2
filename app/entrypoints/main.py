from fastapi import FastAPI

from app.config import config
from app.routers import admin_router_v1, public_router_v1


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Registers versioned routers and attaches utility endpoints that are
    excluded from the OpenAPI schema (health check and root info).
    """
    app = FastAPI(
        debug=config.app.debug,
        title=config.app.title,
    )

    app.include_router(admin_router_v1)
    app.include_router(public_router_v1)

    @app.get("/health_check", tags=["monitoring"], include_in_schema=False)
    async def health_check() -> dict[str, bool | str]:
        """Liveness probe — returns 200 as long as the process is up."""
        return {"status": True, "message": f"The service {app.title} is running!"}

    @app.get("/", tags=["root"], include_in_schema=False)
    async def root() -> dict[str, str]:
        """Returns service metadata and links to interactive API documentation."""
        return {"title": app.title, "swagger": "/docs", "redocly": "/redoc"}

    return app
