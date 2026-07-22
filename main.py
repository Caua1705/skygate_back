import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from src.api.endpoints import airports, health, routes
from src.core.config import get_settings


settings = get_settings()
logger = logging.getLogger("skygate.database")

app = FastAPI(title="SkyGate API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(airports.router)
app.include_router(routes.router)


@app.exception_handler(OperationalError)
async def handle_database_unavailable(request: Request, error: OperationalError) -> JSONResponse:
    logger.error(
        "Database unavailable while handling %s %s",
        request.method,
        request.url.path,
        exc_info=(type(error), error, error.__traceback__),
    )
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
    logger.error(
        "Database operation failed while handling %s %s",
        request.method,
        request.url.path,
        exc_info=(type(error), error, error.__traceback__),
    )
    return JSONResponse(status_code=500, content={"detail": "Database operation failed"})
