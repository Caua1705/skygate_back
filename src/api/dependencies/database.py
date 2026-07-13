from collections.abc import Generator

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.db.session import SessionLocal


def get_database() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()
