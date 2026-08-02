"""Application entry point."""

import uvicorn
from fastapi import FastAPI

from configuration.application import ApplicationSettings
from configuration.fastapi import FastapiSettings
from utils.import_router import import_router
from utils.init_logging import init_logging, lifespan

from observability import LOG_MSG


def create_app() -> FastAPI:
    """Start the application."""
    init_logging()

    """Create and configure the FastAPI application."""
    service_name = FastapiSettings.get_settings().service_name
    app_version = ApplicationSettings.get_settings().app_version
    app = FastAPI(
        title=service_name,
        version=app_version,
        lifespan=lifespan,
    )
    app = import_router(app)

    return app


def main() -> None:
    """Start the FastAPI application with Uvicorn."""
    settings = ApplicationSettings.get_settings()

    uvicorn.run(
        "run:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_config=None,
    )


app = create_app()

if __name__ == "__main__":
    main()
