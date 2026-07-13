from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_database
from src.repositories.airport_repository import AirportRepository
from src.repositories.business_repository import BusinessRepository
from src.repositories.graph_repository import GraphRepository
from src.repositories.route_session_repository import RouteSessionRepository
from src.schemas.route_schema import RouteRequest, RouteResponse
from src.services.airport_service import AirportNotFoundError
from src.services.dijkstra_service import RouteNotFoundError
from src.services.route_service import BusinessNotFoundError, NodeNotFoundError, RouteService


router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/calculate", response_model=RouteResponse)
def calculate_route(request: RouteRequest, session: Session = Depends(get_database)):
    service = RouteService(
        AirportRepository(session),
        GraphRepository(session),
        BusinessRepository(session),
        RouteSessionRepository(session),
    )
    try:
        return service.calculate(request)
    except (AirportNotFoundError, NodeNotFoundError, BusinessNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RouteNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
