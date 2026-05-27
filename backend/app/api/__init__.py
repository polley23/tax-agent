"""Aggregate all FastAPI routers into a single router."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.calculation import router as calc_router
from app.api.data import router as data_router
from app.api.health import router as health_router
from app.api.upload import router as upload_router

# Main router that combines all sub-routers
api_router = APIRouter()
api_router.include_router(health_router)       # /health
api_router.include_router(auth_router)         # /auth/*
api_router.include_router(data_router)         # /profile, /income, /deductions
api_router.include_router(upload_router)       # /documents/*
api_router.include_router(calc_router)         # /calculation/*

__all__ = ["api_router"]
