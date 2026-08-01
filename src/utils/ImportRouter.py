"""import all routers required by the FastAPI app"""

from fastapi import FastAPI

from src.api.routers.FastapiStatus import router as fastapi_status_router
from src.api.routers.Favicon import router as favicon_router
from src.api.routers.Readme import router as readme_router

def import_router(app: FastAPI) -> FastAPI:
    app.include_router(fastapi_status_router)
    app.include_router(favicon_router)
    app.include_router(readme_router)

    return app