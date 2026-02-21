"""
Memory Soil — The Earth That Remembers Everything

Async SQLAlchemy setup with SQLite. Nothing is truly deleted, only composted.
"""

from __future__ import annotations

import logging
import os

from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models.db_models import Base, GardenState

logger = logging.getLogger("w0rd.soil")

DATABASE_URL = os.getenv("W0RD_DATABASE_URL", "sqlite+aiosqlite:///./w0rd_garden.db")

engine = create_async_engine(DATABASE_URL, echo=False)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode and set busy timeout for SQLite concurrency."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables and ensure a GardenState singleton exists."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA journal_mode=WAL"))

    async with async_session() as session:
        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        if result.scalar_one_or_none() is None:
            session.add(GardenState(id="garden"))
            await session.commit()
            logger.info("Garden state initialized — the soil is ready")


async def get_session() -> AsyncSession:
    """FastAPI dependency for DB sessions."""
    async with async_session() as session:
        yield session


async def shutdown_db() -> None:
    """Dispose of the engine on shutdown."""
    await engine.dispose()
    logger.info("Memory Soil connection closed")
