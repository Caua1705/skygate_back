import os

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://postgres:password@localhost:5432/postgres"


def _database_url_is_valid(value: str | None) -> bool:
    if not value:
        return False
    try:
        make_url(value)
    except ArgumentError:
        return False
    return True


if not _database_url_is_valid(os.environ.get("DATABASE_URL")):
    os.environ["DATABASE_URL"] = DEFAULT_TEST_DATABASE_URL