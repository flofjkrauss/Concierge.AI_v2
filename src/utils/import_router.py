"""import all routers required by the FastAPI app"""

from fastapi import FastAPI

from api.routers.fastapi_status import router as fastapi_status_router
from api.routers.favicon import router as favicon_router
from api.routers.readme import router as readme_router


def import_router(app: FastAPI) -> FastAPI:
    app.include_router(fastapi_status_router)
    app.include_router(favicon_router)
    app.include_router(readme_router)

    return app
