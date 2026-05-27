"""Tax calculation schemas."""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class CalculationRequest(BaseSchema):
    financial_year: int = Field(examples=[2025])


class CalculationOut(BaseSchema):
    id: int
    user_id: int
    financial_year: int
    status: str
    steps: list[dict[str, Any]]
    result: dict[str, Any]
