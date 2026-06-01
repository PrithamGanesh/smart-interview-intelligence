"""PostgreSQL connection management with SQLAlchemy."""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Async engine for async operations
async_engine = None
async_session_maker = None

# Sync engine for blocking operations
sync_engine = None
sync_session_maker = None


async def init_db() -> None:
    """Initialize database connection pool."""
    global async_engine, async_session_maker
    
    logger.info("Initializing PostgreSQL connection pool")
    
    async_engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=settings.DEBUG,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,  # Test connections before using
        pool_recycle=3600,   # Recycle connections after 1 hour
    )
    
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    logger.info("Database pool initialized")


async def close_db() -> None:
    """Close database connections."""
    global async_engine
    
    if async_engine:
        await async_engine.dispose()
        logger.info("Database connections closed")


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


def init_sync_db() -> None:
    """Initialize synchronous database connection (for workers)."""
    global sync_engine, sync_session_maker
    
    logger.info("Initializing synchronous PostgreSQL connection pool")
    
    sync_engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=pool.QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    
    sync_session_maker = sessionmaker(bind=sync_engine, expire_on_commit=False)
    
    logger.info("Synchronous database pool initialized")


@contextmanager
def get_sync_session() -> Generator:
    """Get synchronous database session."""
    if sync_session_maker is None:
        raise RuntimeError("Sync database not initialized. Call init_sync_db() first.")
    
    session = sync_session_maker()
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


# Health check function
async def check_db_health() -> bool:
    """Check if database is accessible."""
    try:
        async with get_async_session() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
