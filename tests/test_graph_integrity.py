from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from src.models.airport_edge_model import AirportEdge
from src.models.airport_node_model import AirportNode


def _unique_column_sets(table) -> set[tuple[str, ...]]:
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_models_protect_duplicate_edges():
    unique_columns = _unique_column_sets(AirportEdge.__table__)

    assert ("airport_id", "from_node_id", "to_node_id") in unique_columns


def test_models_require_edge_nodes_from_same_airport():
    node_unique_columns = _unique_column_sets(AirportNode.__table__)
    foreign_key_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in AirportEdge.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint) and len(constraint.columns) == 2
    }

    assert ("airport_id", "id") in node_unique_columns
    assert ("airport_id", "from_node_id") in foreign_key_columns
    assert ("airport_id", "to_node_id") in foreign_key_columns

