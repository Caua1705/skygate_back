from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.airport_edge_model import AirportEdge
from src.models.airport_node_model import AirportNode


class GraphRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_nodes(self, airport_id: UUID) -> list[AirportNode]:
        statement = select(AirportNode).where(AirportNode.airport_id == airport_id).order_by(AirportNode.code)
        return list(self.session.scalars(statement))

    def list_edges(self, airport_id: UUID) -> list[AirportEdge]:
        statement = (
            select(AirportEdge)
            .where(AirportEdge.airport_id == airport_id)
            .order_by(AirportEdge.from_node_id, AirportEdge.to_node_id)
        )
        return list(self.session.scalars(statement))
