"""Application entry point."""

import uvicorn
from fastapi import FastAPI

from src.configuration.fastapi import FastapiSettings
from src.configuration.application import ApplicationSettings

from src.utils.ImportRouter import import_router


def create_app() -> FastAPI:
    """Start the application."""
    print("Application started.")

    """Create and configure the FastAPI application."""
    service_name = FastapiSettings.get_settings().service_name
    app_version = ApplicationSettings.get_settings().app_version
    app = FastAPI(title=service_name, version=app_version)
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
    )

app = create_app()

if __name__ == "__main__":
    main()