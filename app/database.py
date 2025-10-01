#!/usr/bin/env python3
"""
Database configuration and connection management
"""

import logging
import time
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Database configuration
settings = get_settings()

# Create SQLAlchemy engines
engine = create_engine(
    settings.database_url.replace("+asyncpg", ""),  # Sync engine for Alembic
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections after 5 minutes
    pool_size=20,        # Connection pool size
    max_overflow=0,      # Don't allow overflow connections
    echo=False           # Set to True for SQL debugging
)

# Async engine for FastAPI - ensure proper asyncpg configuration
database_url = settings.database_url
if not database_url.startswith("postgresql+asyncpg://"):
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://")

async_engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=5,
    echo=False,
    future=True  # Use future engine for SQLAlchemy 2.0 style
)

# Create SessionLocal classes
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Use async_sessionmaker for SQLAlchemy 2.0 best practices
from sqlalchemy.ext.asyncio import async_sessionmaker

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Critical for async - prevents greenlet errors
    autoflush=False,
    autocommit=False
)

# Create Base class for ORM models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Used with FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get async database session.
    Used with FastAPI dependency injection.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Async database session error: {e}")
            await session.rollback()
            raise


class AsyncDatabaseSession:
    """Async context manager for database sessions"""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self) -> AsyncSession:
        self.session = AsyncSessionLocal()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
            await self.session.close()


def get_async_db_session():
    """Get an async database session context manager"""
    return AsyncDatabaseSession()

def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            # Execute a simple query to test connection
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
            return True
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return False
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        return False

def wait_for_database(max_retries: int = 30, delay: int = 2) -> bool:
    """
    Wait for database to become available.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between attempts in seconds
        
    Returns:
        bool: True if database is available, False if max retries reached
    """
    logger.info("⏳ Waiting for database connection...")
    
    for attempt in range(max_retries):
        try:
            if check_database_connection():
                logger.info("✅ Database connection established")
                return True
        except Exception as e:
            logger.debug(f"Database connection attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:  # Don't sleep on the last attempt
            logger.info(f"⏳ Retrying database connection... (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
    
    logger.error("❌ Failed to establish database connection after maximum retries")
    return False

def get_database_info() -> dict:
    """
    Get database information for monitoring and debugging.
    
    Returns:
        dict: Database information including connection status and settings
    """
    try:
        is_connected = check_database_connection()
        
        info = {
            "connected": is_connected,
            "url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "hidden",  # Hide credentials
            "engine_info": {
                "pool_size": engine.pool.size(),
                "pool_checked_in": engine.pool.checkedin(),
                "pool_checked_out": engine.pool.checkedout(),
                "pool_overflow": engine.pool.overflow(),
            }
        }
        
        if is_connected:
            with engine.connect() as connection:
                # Get database version
                try:
                    result = connection.execute(text("SELECT version()"))
                    version = result.fetchone()
                    info["version"] = version[0] if version else "unknown"
                except Exception as e:
                    info["version"] = f"error: {e}"
                
                # Get current database name
                try:
                    result = connection.execute(text("SELECT current_database()"))
                    db_name = result.fetchone()
                    info["database_name"] = db_name[0] if db_name else "unknown"
                except Exception as e:
                    info["database_name"] = f"error: {e}"
        
        return info
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return {
            "connected": False,
            "error": str(e),
            "url": "unknown"
        }

class DatabaseManager:
    """Database manager class for advanced operations"""
    
    @staticmethod
    def create_tables():
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create database tables: {e}")
            return False
    
    @staticmethod
    def drop_tables():
        """Drop all database tables (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=engine)
            logger.warning("⚠️ All database tables dropped")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to drop database tables: {e}")
            return False
    
    @staticmethod
    def get_table_info():
        """Get information about database tables"""
        try:
            with engine.connect() as connection:
                # Get table names
                result = connection.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """))
                
                tables = [row[0] for row in result.fetchall()]
                
                table_info = {}
                for table_name in tables:
                    # Get row count for each table
                    try:
                        count_result = connection.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        count = count_result.fetchone()[0]
                        table_info[table_name] = {"row_count": count}
                    except Exception as e:
                        table_info[table_name] = {"error": str(e)}
                
                return table_info
                
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            return {"error": str(e)}

# Initialize database manager instance
db_manager = DatabaseManager()