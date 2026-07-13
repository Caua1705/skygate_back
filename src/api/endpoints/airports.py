from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_database
from src.repositories.airport_repository import AirportRepository
from src.repositories.business_repository import BusinessRepository
from src.repositories.graph_repository import GraphRepository
from src.schemas.airport_schema import AirportResponse
from src.schemas.graph_schema import AirportMapResponse
from src.services.airport_service import AirportNotFoundError, AirportService


router = APIRouter(prefix="/airports", tags=["airports"])


def get_airport_service(session: Session) -> AirportService:
    return AirportService(
        AirportRepository(session),
        GraphRepository(session),
        BusinessRepository(session),
    )


@router.get("/{slug}", response_model=AirportResponse)
def get_airport(slug: str, session: Session = Depends(get_database)):
    try:
        return get_airport_service(session).get_airport(slug)
    except AirportNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{slug}/map", response_model=AirportMapResponse)
def get_airport_map(slug: str, session: Session = Depends(get_database)):
    try:
        return get_airport_service(session).get_map(slug)
    except AirportNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

