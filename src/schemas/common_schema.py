from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class DatabaseHealthResponse(HealthResponse):
    database: str


class MessageResponse(BaseModel):
    message: str
