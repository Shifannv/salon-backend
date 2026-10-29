"""Health-check schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str


class VersionResponse(BaseModel):
    """Non-secret, immutable image identity."""

    version: str
    commit_sha: str


class DatabaseHealthResponse(BaseModel):
    """Database health-check response."""

    status: str
    database: str


class RedisHealthResponse(BaseModel):
    """Redis health-check response."""

    status: str
    redis: str
