"""Data-management router — income, deductions, profile."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.perm import require_owner
from app.schemas.deduction import DeductionCreate, DeductionOut
from app.schemas.income import IncomeCreate, IncomeOut
from app.schemas.user import ProfileCreate, ProfileOut
from db.models import Deduction, IncomeSource, Profile, User
from db.session import get_db

router = APIRouter(tags=["data"])


# -------------------- Profile ------------- ----

@router.post("/profile", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: ProfileCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await session.execute(select(Profile).where(Profile.user_id == current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists",
        )
    profile = Profile(**payload.model_dump(), user_id=current_user.id)
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
    return profile


@router.get("/profile", response_model=ProfileOut)
async def get_profile(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


# -------------------- Income ------------- ----

@router.post("/income", response_model=IncomeOut, status_code=status.HTTP_201_CREATED)
async def add_income(
    payload: IncomeCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    income = IncomeSource(**payload.model_dump(), user_id=current_user.id)
    session.add(income)
    await session.flush()
    await session.refresh(income)
    return income


@router.get("/income")
async def list_income(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await session.execute(
        select(IncomeSource)
        .where(IncomeSource.user_id == current_user.id)
        .order_by(IncomeSource.id)
    )
    return rows.scalars().all()


@router.get("/income/{id}", response_model=IncomeOut)
async def get_income(
    row: IncomeSource = Depends(require_owner(IncomeSource)),
):
    """Get a single income source — ownership verified by the dependency."""
    return row


@router.delete("/income/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_income(
    row: IncomeSource = Depends(require_owner(IncomeSource)),
    session: AsyncSession = Depends(get_db),
):
    """Delete an income source — ownership verified by the dependency."""
    await session.delete(row)
    await session.flush()


# -------------------- Deductions ------------- ----

@router.post("/deductions", response_model=DeductionOut, status_code=status.HTTP_201_CREATED)
async def add_deduction(
    payload: DeductionCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deduction = Deduction(**payload.model_dump(), user_id=current_user.id)
    session.add(deduction)
    await session.flush()
    await session.refresh(deduction)
    return deduction


@router.get("/deductions")
async def list_deductions(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await session.execute(
        select(Deduction)
        .where(Deduction.user_id == current_user.id)
        .order_by(Deduction.id)
    )
    return rows.scalars().all()


@router.get("/deductions/{id}", response_model=DeductionOut)
async def get_deduction(
    row: Deduction = Depends(require_owner(Deduction)),
):
    """Get a single deduction — ownership verified by the dependency."""
    return row


@router.delete("/deductions/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deduction(
    row: Deduction = Depends(require_owner(Deduction)),
    session: AsyncSession = Depends(get_db),
):
    """Delete a deduction — ownership verified by the dependency."""
    await session.delete(row)
    await session.flush()
