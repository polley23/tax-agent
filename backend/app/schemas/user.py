"""User and profile schemas."""

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


# ---------------------------------------------
# User
# ---------------------------------------------

class UserCreate(BaseSchema):
    email: str = Field(examples=["user@example.com"])
    password: str = Field(min_length=8)


class UserOut(BaseSchema):
    id: int
    email: str
    is_active: bool


# ---------------------------------------------
# Profile
# ---------------------------------------------

class ProfileCreate(BaseSchema):
    jurisdiction: str = Field(description="US or UK")
    filing_status: str = Field(description="single, married_joint, …")
    financial_year: int = Field(examples=[2025])
    frequency: str = Field(description="annual, quarterly, monthly")


class ProfileOut(BaseSchema):
    id: int
    user_id: int
    jurisdiction: str
    filing_status: str
    financial_year: int
    frequency: str
