from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.airport_business_model import AirportBusiness
from src.models.airport_node_model import AirportNode


class BusinessRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_by_airport(self, airport_id: UUID, active_only: bool = True) -> list[AirportBusiness]:
        statement = select(AirportBusiness).join(AirportNode, AirportBusiness.node_id == AirportNode.id)
        statement = statement.where(AirportNode.airport_id == airport_id)
        if active_only:
            statement = statement.where(AirportBusiness.is_active.is_(True))
        return list(self.session.scalars(statement))

    def get_active_by_id_for_airport(self, business_id: UUID, airport_id: UUID) -> AirportBusiness | None:
        statement = (
            select(AirportBusiness)
            .join(AirportNode, AirportBusiness.node_id == AirportNode.id)
            .where(
                AirportBusiness.id == business_id,
                AirportBusiness.is_active.is_(True),
                AirportNode.airport_id == airport_id,
            )
        )
        return self.session.scalar(statement)

    def list_active_by_category_for_airport(self, category: str, airport_id: UUID) -> list[AirportBusiness]:
        statement = (
            select(AirportBusiness)
            .join(AirportNode, AirportBusiness.node_id == AirportNode.id)
            .where(
                AirportBusiness.category == category,
                AirportBusiness.is_active.is_(True),
                AirportNode.airport_id == airport_id,
            )
            .order_by(AirportBusiness.id)
        )
        return list(self.session.scalars(statement))
