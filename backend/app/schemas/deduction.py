"""Deduction schemas."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class DeductionCreate(BaseSchema):
    financial_year: int = Field(examples=[2025])
    category: str = Field(examples=["charitable", "mortgage_interest", "student_loan_interest"])
    amount: float = Field(gt=0)
    description: str = ""
    metadata_json: dict[str, Any] | None = None


class DeductionOut(BaseSchema):
    id: int
    user_id: int
    financial_year: int
    category: str
    amount: float
    description: str
    metadata_json: dict[str, Any]
