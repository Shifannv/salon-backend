"""Health-check schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str


class DatabaseHealthResponse(BaseModel):
    """Database health-check response."""

    status: str
    database: str
