from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import get_settings
from src.core.constants import DATABASE_CONNECT_TIMEOUT_SECONDS


settings = get_settings()
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_timeout=DATABASE_CONNECT_TIMEOUT_SECONDS,
    connect_args={"connect_timeout": DATABASE_CONNECT_TIMEOUT_SECONDS},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
