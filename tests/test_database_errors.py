import asyncio
from types import SimpleNamespace

from sqlalchemy.exc import OperationalError

from main import handle_database_unavailable
from src.repositories.route_session_repository import RouteSessionRepository


class FailingSession:
    def __init__(self):
        self.rollback_called = False

    def add(self, instance):
        self.instance = instance

    def commit(self):
        raise OperationalError("INSERT", {}, ConnectionError("database unavailable"))

    def rollback(self):
        self.rollback_called = True


def test_route_session_repository_rolls_back_failed_write():
    session = FailingSession()

    try:
        RouteSessionRepository(session).create()
    except OperationalError:
        pass

    assert session.rollback_called is True


def test_operational_error_handler_returns_safe_503():
    request = SimpleNamespace(method="GET", url=SimpleNamespace(path="/health/database"))
    error = OperationalError("SELECT 1", {}, ConnectionError("secret database host"))

    response = asyncio.run(handle_database_unavailable(request, error))

    assert response.status_code == 503
    assert response.body == b'{"detail":"Database unavailable"}'
    assert b"secret database host" not in response.body
