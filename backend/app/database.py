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

# Database URL from environment
POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5442/postgres"
)

# Create async engine
engine = create_async_engine(
    POSTGRES_URL,
    echo=False,  # Set to True for SQL query logging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.
    
    Usage:
        @app.get("/api/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session here
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


async def init_db():
    """
    Initialize database - create all tables.
    Call this on application startup.
    """
    async with engine.begin() as conn:
        # Import models to register them with Base
        from app.models import MonitoringJob, MonitoringEvent, MonitoringAlert
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created/verified")


async def close_db():
    """
    Close database connections.
    Call this on application shutdown.
    """
    await engine.dispose()
    print("✅ Database connections closed")