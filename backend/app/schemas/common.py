"""Common pydantic schema types."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class BaseSchema(BaseModel):
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# API envelope types
# ---------------------------------------------------------------------------

class ErrorDetail(BaseSchema):
    code: str
    detail: str


class PaginatedResponse(BaseSchema):
    """Generic paginated list envelope."""
    items: list[Any]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseSchema):
    status: str
    version: str
    database: str
    timestamp: datetime
