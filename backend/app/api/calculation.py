"""Tax-calculation router — stub for Phase 2 deterministic engine."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.schemas.calculation import CalculationOut
from db.models import User
from db.session import get_db

router = APIRouter(prefix="/calculation", tags=["calculation"])


@router.post("")
async def trigger_calculation(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stub endpoint — returns empty calculation skeleton.

    The real deterministic engine runs in Phase 2.
    """
    return CalculationOut(
        id=0,
        user_id=current_user.id,
        financial_year=2025,
        status="draft",
        steps=[],
        result={"message": "Deterministic engine not yet wired — Phase 2"},
    )
