"""Document schemas."""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class DocumentOut(BaseSchema):
    id: int
    user_id: int
    doc_type: str
    status: str
    uploaded_at: str
    extracted_json: dict[str, Any]
