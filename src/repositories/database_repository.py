from sqlalchemy import text
from sqlalchemy.orm import Session


class DatabaseRepository:
    def __init__(self, session: Session):
        self.session = session

    def ping(self) -> None:
        self.session.execute(text("SELECT 1"))
