"""Income source schemas."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class IncomeCreate(BaseSchema):
    financial_year: int = Field(examples=[2025])
    form_type: str = Field(examples=["w2", "1099-misc", "1099-nec"])
    source_label: str = Field(examples=["Acme Corp", "Upwork"])
    amount: float = Field(gt=0, description="Amount in currency units")
    metadata_json: dict[str, Any] | None = None


class IncomeOut(BaseSchema):
    id: int
    user_id: int
    financial_year: int
    form_type: str
    source_label: str
    amount: float
    metadata_json: dict[str, Any]
