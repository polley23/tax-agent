"""Authentication request/response schemas."""

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class LoginRequest(BaseSchema):
    email: str
    password: str


class LoginResponse(BaseSchema):
    access_token: str
    token_type: str
