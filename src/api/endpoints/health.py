from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_database
from src.repositories.database_repository import DatabaseRepository
from src.schemas.common_schema import DatabaseHealthResponse, HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/database", response_model=DatabaseHealthResponse)
def database_health_check(session: Session = Depends(get_database)) -> dict[str, str]:
    DatabaseRepository(session).ping()
    return {"status": "ok", "database": "available"}
