from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.models.route_session_model import RouteSession


class RouteSessionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **data) -> RouteSession:
        route_session = RouteSession(**data)
        self.session.add(route_session)
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        self.session.refresh(route_session)
        return route_session

