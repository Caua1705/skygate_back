"""Check the SkyGate database connection without printing secrets."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

from src.core.config import get_settings
from src.core.constants import DATABASE_CONNECT_TIMEOUT_SECONDS


def _mask(value: str | None) -> str:
    if not value:
        return "<empty>"
    if len(value) <= 2:
        return "*" * len(value)
    return f"{value[0]}***{value[-1]}"


def _connection_label(database_url: str) -> str:
    url = make_url(database_url)
    return (
        f"host={_mask(url.host)}, "
        f"database={_mask(url.database)}, "
        f"user={_mask(url.username)}, "
        f"driver={url.drivername}"
    )


def main() -> int:
    settings = get_settings()
    try:
        print("Database config: " + _connection_label(settings.database_url))
    except ArgumentError:
        print("Database config: invalid DATABASE_URL format")
        print("Details omitted to avoid exposing secrets. Expected: postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE")
        return 1

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_timeout=DATABASE_CONNECT_TIMEOUT_SECONDS,
        connect_args={"connect_timeout": DATABASE_CONNECT_TIMEOUT_SECONDS},
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        print(f"Connection failed: {exc.__class__.__name__}")
        print("Details omitted to avoid exposing secrets. Check DATABASE_URL credentials and database availability.")
        return 1
    finally:
        engine.dispose()

    print("Connection passed: SELECT 1 succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())