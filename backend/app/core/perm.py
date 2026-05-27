"""Authorization helpers — resource ownership guard."""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.api.auth import get_current_user
from db.models import User


def require_owner(model: type[DeclarativeBase]) -> Callable[..., Any]:
    """Return a FastAPI dependency that loads *model* by ID and verifies ownership.

    Usage: ``row: IncomeSource = Depends(require_owner(IncomeSource))``
    """
    async def _guard(id: int, session: AsyncSession, current_user: User = Depends(get_current_user)):
        result = await session.execute(select(model).where(model.id == id))
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
        if row.user_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return row
    return _guard
