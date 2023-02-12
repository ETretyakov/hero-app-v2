from fastapi import FastAPI

from app.config import config
from app.routers import admin_router_v1, public_router_v1


def create_app():
    app = FastAPI(
        debug=config.app.debug,
        title=config.app.title,
    )

    app.include_router(admin_router_v1)
    app.include_router(public_router_v1)

    @app.get("/health_check", tags=["monitoring"], include_in_schema=False)
    async def health_check():
        return {
            "status": True,
            "message": f"The service {app.title} is running!",
        }

    @app.get("/", tags=["root"], include_in_schema=False)
    async def root():
        return {
            "title": app.title,
            "swagger": "/docs",
            "redocly": "/redoc"
        }

    return app
