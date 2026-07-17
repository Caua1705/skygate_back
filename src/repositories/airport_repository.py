from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.airport_model import Airport


class AirportRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> list[Airport]:
        statement = select(Airport).order_by(Airport.name)
        return list(self.session.scalars(statement))

    def get_by_slug(self, slug: str) -> Airport | None:
        statement = select(Airport).where(Airport.slug == slug)
        return self.session.scalar(statement)

