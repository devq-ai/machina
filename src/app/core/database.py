"""
Database Module for Machina Registry Service

This module provides database connection management, session handling, and ORM
configuration using SQLAlchemy with async support for PostgreSQL. It implements
DevQ.ai's standard database patterns with proper connection pooling, transaction
management, and error handling.

Features:
- Async PostgreSQL connection using asyncpg driver
- SQLAlchemy ORM with async sessions
- Connection pooling and lifecycle management
- Transaction management with automatic rollback
- Database initialization and health checking
- Logfire integration for database observability
"""

import asyncio
import time
from typing import AsyncGenerator, Optional, Dict, Any
from contextlib import asynccontextmanager

import logfire
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import text, event
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.core.exceptions import DatabaseError


# Create the declarative base for all models
Base = declarative_base()

# Global engine and session factory
engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


class DatabaseManager:
    """
    Database manager for handling SQLAlchemy async operations.

    Provides centralized database connection management, session handling,
    and health monitoring for the Machina Registry Service.
    """

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """
        Initialize the database connection and session factory.

        Creates the async engine with proper configuration and sets up
        the session factory for dependency injection.

        Raises:
            DatabaseError: If database initialization fails
        """
        if self._is_initialized:
            logfire.info("Database already initialized, skipping...")
            return

        try:
            with logfire.span("Database initialization"):
                # Create async engine with optimized configuration
                self.engine = create_async_engine(
                    settings.DATABASE_URI,
                    echo=settings.DEBUG,
                    future=True,
                    pool_size=settings.POOL_SIZE,
                    max_overflow=settings.POOL_OVERFLOW,
                    pool_pre_ping=True,
                    pool_recycle=300,  # Recycle connections every 5 minutes
                    connect_args={
                        "server_settings": {
                            "application_name": settings.PROJECT_NAME,
                        }
                    }
                )

                # Create session factory
                self.session_factory = async_sessionmaker(
                    bind=self.engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autoflush=True,
                    autocommit=False
                )

                # Set global references
                global engine, AsyncSessionLocal
                engine = self.engine
                AsyncSessionLocal = self.session_factory

                # Test the connection
                await self.health_check()

                self._is_initialized = True

                logfire.info(
                    "Database initialized successfully",
                    database_url=settings.POSTGRES_SERVER,
                    pool_size=settings.POOL_SIZE,
                    max_overflow=settings.POOL_OVERFLOW
                )

        except Exception as e:
            logfire.error("Database initialization failed", error=str(e))
            raise DatabaseError(
                operation="initialize",
                message=f"Failed to initialize database: {str(e)}",
                cause=e
            )

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the database connection.

        Returns:
            Dict containing health status and connection information

        Raises:
            DatabaseError: If health check fails
        """
        if not self.engine:
            raise DatabaseError(
                operation="health_check",
                message="Database not initialized"
            )

        try:
            with logfire.span("Database health check"):
                async with self.engine.begin() as conn:
                    # Test basic connectivity
                    result = await conn.execute(text("SELECT 1 as health_check"))
                    health_value = result.scalar()

                    # Get database info
                    version_result = await conn.execute(text("SELECT version()"))
                    db_version = version_result.scalar()

                    # Get connection pool info
                    pool = self.engine.pool

                    health_info = {
                        "status": "healthy" if health_value == 1 else "unhealthy",
                        "database_version": db_version,
                        "connection_pool": {
                            "size": pool.size(),
                            "checked_in": pool.checkedin(),
                            "checked_out": pool.checkedout(),
                            "overflow": pool.overflow(),
                            "invalid": pool.invalid()
                        },
                        "settings": {
                            "pool_size": settings.POOL_SIZE,
                            "max_overflow": settings.POOL_OVERFLOW,
                            "database_name": settings.POSTGRES_DB
                        }
                    }

                    logfire.info("Database health check completed", **health_info)
                    return health_info

        except Exception as e:
            logfire.error("Database health check failed", error=str(e))
            raise DatabaseError(
                operation="health_check",
                message=f"Database health check failed: {str(e)}",
                cause=e
            )

    async def close(self) -> None:
        """
        Close the database engine and all connections.

        Should be called during application shutdown to clean up resources.
        """
        if self.engine:
            with logfire.span("Database shutdown"):
                await self.engine.dispose()
                self.engine = None
                self.session_factory = None
                self._is_initialized = False

                global engine, AsyncSessionLocal
                engine = None
                AsyncSessionLocal = None

                logfire.info("Database connections closed successfully")


# Global database manager instance
db_manager = DatabaseManager()


async def init_db() -> None:
    """
    Initialize the database connection.

    This function should be called during application startup.
    """
    await db_manager.initialize()


async def close_db() -> None:
    """
    Close the database connections.

    This function should be called during application shutdown.
    """
    await db_manager.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session for dependency injection.

    This function creates a new database session and ensures proper
    transaction management with automatic rollback on exceptions.

    Yields:
        AsyncSession: Database session for use in endpoints and services

    Raises:
        DatabaseError: If session creation fails
    """
    if not AsyncSessionLocal:
        raise DatabaseError(
            operation="get_session",
            message="Database not initialized. Call init_db() first."
        )

    async with AsyncSessionLocal() as session:
        try:
            with logfire.span("Database session"):
                yield session
        except Exception as e:
            logfire.warning("Database session error, rolling back", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as a context manager.

    Alternative to get_db() for use outside of FastAPI dependency injection.
    Provides automatic session management with proper cleanup.

    Usage:
        async with get_db_session() as db:
            result = await db.execute(select(Model))

    Yields:
        AsyncSession: Database session with automatic cleanup
    """
    if not AsyncSessionLocal:
        raise DatabaseError(
            operation="get_session",
            message="Database not initialized. Call init_db() first."
        )

    async with AsyncSessionLocal() as session:
        try:
            with logfire.span("Database context session"):
                yield session
        except Exception as e:
            logfire.warning("Database context session error, rolling back", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> Dict[str, Any]:
    """
    Check database health status.

    Returns:
        Dict containing health information
    """
    return await db_manager.health_check()


# Event listeners for logging and observability
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL queries for debugging and observability."""
    if settings.DEBUG:
        logfire.debug(
            "SQL Query",
            statement=statement,
            parameters=parameters if settings.DEBUG else "***",
            executemany=executemany
        )


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL query completion time."""
    if settings.DEBUG and hasattr(context, '_query_start_time'):
        duration = time.time() - context._query_start_time
        if duration > 1.0:  # Log slow queries
            logfire.warning(
                "Slow SQL Query",
                duration=duration,
                statement=statement[:100] + "..." if len(statement) > 100 else statement
            )


# Database session dependency for FastAPI
def get_database_session():
    """
    FastAPI dependency factory for database sessions.

    Returns:
        Callable that yields database sessions
    """
    return get_db


# Database utilities
async def create_all_tables() -> None:
    """
    Create all database tables.

    This function creates all tables defined by SQLAlchemy models.
    Should only be used in development or for initial setup.
    """
    if not engine:
        raise DatabaseError(
            operation="create_tables",
            message="Database not initialized"
        )

    try:
        with logfire.span("Create database tables"):
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logfire.info("Database tables created successfully")

    except Exception as e:
        logfire.error("Failed to create database tables", error=str(e))
        raise DatabaseError(
            operation="create_tables",
            message=f"Failed to create tables: {str(e)}",
            cause=e
        )


async def drop_all_tables() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data. Use with extreme caution.
    Should only be used in development or testing.
    """
    if not engine:
        raise DatabaseError(
            operation="drop_tables",
            message="Database not initialized"
        )

    if settings.is_production:
        raise DatabaseError(
            operation="drop_tables",
            message="Cannot drop tables in production environment"
        )

    try:
        with logfire.span("Drop database tables"):
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

            logfire.warning("Database tables dropped")

    except Exception as e:
        logfire.error("Failed to drop database tables", error=str(e))
        raise DatabaseError(
            operation="drop_tables",
            message=f"Failed to drop tables: {str(e)}",
            cause=e
        )
