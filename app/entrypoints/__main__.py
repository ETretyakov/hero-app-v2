import uvicorn

from app.config import config


uvicorn.run(
    app="app.entrypoints.main:create_app",
    factory=True,
    host=config.app.host,
    port=config.app.port,
    reload=config.app.reload,
)
