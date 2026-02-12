"""
SQLAlchemy async database setup for Sentinel backend.
Handles connection pooling, session management, and base model.
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# BASE CLASS FOR ORM MODELS
# ==============================================================================

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    
    All models in db_models.py should inherit from this class.
    """
    pass


# ==============================================================================
# DATABASE ENGINE & SESSION FACTORY
# ==============================================================================

# Database URL from environment (required — no insecure defaults)
POSTGRES_URL = os.getenv("POSTGRES_URL")
if not POSTGRES_URL:
    raise RuntimeError(
        "POSTGRES_URL environment variable is not set. "
        "Please set it to your PostgreSQL connection string, e.g.:\n"
        "  POSTGRES_URL=postgresql+asyncpg://user:pass@host:port/dbname"
    )

# Create async engine with connection pooling
engine = create_async_engine(
    POSTGRES_URL,
    echo=False,             # Set to True for SQL query logging (dev mode)
    pool_size=10,           # Max connections in pool
    max_overflow=20,        # Max overflow connections
    pool_pre_ping=True,     # Verify connections before using
    pool_recycle=3600,      # Recycle connections after 1 hour
)

# Session factory for dependency injection
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,        # Manual commits for transaction control
    autoflush=False,         # Manual flushes for performance
)


# ==============================================================================
# DEPENDENCY INJECTION (FastAPI)
# ==============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Provides automatic transaction management:
    - Commits on success
    - Rolls back on exception
    - Always closes the session
    
    Usage:
        @app.get("/api/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Model))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==============================================================================
# LIFECYCLE MANAGEMENT
# ==============================================================================

async def init_db() -> None:
    """
    Initialize database — create all tables.
    
    Called on application startup (main.py).
    
    IMPORTANT: ORM models are imported INSIDE this function (not at module level)
    to prevent circular import issues. This is a common pattern when database.py
    provides Base but also needs to discover all models for metadata.create_all().
    """
    async with engine.begin() as conn:
        # ✅ FIX: Local import prevents circular dependency
        # (db_models.py imports Base from this file)
        from app.db_models import MonitoringJob, MonitoringEvent, MonitoringAlert  # noqa: F401

        # Create all tables defined in Base.metadata
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created/verified")


async def close_db() -> None:
    """
    Close all database connections.
    
    Called on application shutdown (main.py).
    Ensures graceful cleanup of connection pool.
    """
    await engine.dispose()
    print("✅ Database connections closed")