"""Shared test fixtures."""

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from db.session import Base, async_session_factory, get_db


@pytest.fixture(autouse=True)
def _tmp_media(tmp_path: Path, monkeypatch):
    """Point uploads dir to a temp location for every test."""
    from app.config import get_settings
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    settings_inst = get_settings()
    settings_inst.uploads_path = uploads
    monkeypatch.setattr(settings_inst, "uploads_path", uploads)


# -- Database isolation --

@pytest_asyncio.fixture(autouse=True)
async def _clean_db():
    """Truncate all tables before each test to guarantee isolation."""
    async with async_session_factory() as session:
        await session.begin()
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f"DELETE FROM {table.name}"))
        await session.commit()


@pytest_asyncio.fixture
async def client():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
