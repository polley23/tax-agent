"""Database engine and async session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.db_path_str,
    echo=settings.debug,
    # SQLite WAL not supported with aiosqlite; use defer_foreign_keys for SQLite
    connect_args={"check_same_thread": False},
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async DB session.

    Commit/rollback is handled by the route handler or get_current_user,
    not here, so callers retain control over transaction boundaries.
    """
    async with async_session_factory() as session:
        yield session
