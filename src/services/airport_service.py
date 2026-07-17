from src.repositories.airport_repository import AirportRepository
from src.repositories.business_repository import BusinessRepository
from src.repositories.graph_repository import GraphRepository


class AirportNotFoundError(Exception):
    pass


class AirportService:
    def __init__(
        self,
        airport_repository: AirportRepository,
        graph_repository: GraphRepository,
        business_repository: BusinessRepository,
    ):
        self.airport_repository = airport_repository
        self.graph_repository = graph_repository
        self.business_repository = business_repository

    def list_airports(self):
        return self.airport_repository.list_all()

    def get_airport(self, slug: str):
        airport = self.airport_repository.get_by_slug(slug)
        if airport is None:
            raise AirportNotFoundError(f"Airport '{slug}' not found")
        return airport

    def get_map(self, slug: str) -> dict:
        airport = self.get_airport(slug)
        return {
            "airport": airport,
            "nodes": self.graph_repository.list_nodes(airport.id),
            "edges": self.graph_repository.list_edges(airport.id),
            "businesses": self.business_repository.list_by_airport(airport.id, active_only=False),
        }

