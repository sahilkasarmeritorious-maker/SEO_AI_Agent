from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from typing import AsyncGenerator
import logging
import asyncio
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ASYNC engine with pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,   #echo=settings.DEBUG,  # Log SQL if debug mode
    #poolclass=QueuePool,
    pool_size=20,                          # Max concurrent connections
    max_overflow=10,                       # Extra connections under load
    pool_pre_ping=True,                    # Test connections before use
    pool_recycle=3600,                     # Recycle after 1 hour
    connect_args={
        "timeout": 10,                     # Connection timeout
        "server_settings": {
            "application_name": "website_analyzer"
        }
    }
)

# ASYNC session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # CRITICAL: Keep objects after commit
)

# ASYNC generator for dependency injection
async def get_db() -> AsyncGenerator:
    """Get async database session with error handling."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Database session error: {str(e)}", exc_info=True)
            await session.rollback()
            raise
        finally:
            try:
                await session.close()
            except Exception as close_error:
                logger.error(f"Failed to close database session: {close_error}")


# Health check function
async def check_database_connection() -> bool:
    """Check if database is accessible."""
    try:
        logger.info(f"🔌 Attempting to connect to: {settings.DATABASE_URL}")
        logger.info(f"   Host: localhost")
        logger.info(f"   Port: 5432")
        logger.info(f"   Database: Mydb")
        
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info(" Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}", exc_info=True)  # ← exc_info=True shows full traceback
        return False


# Run Alembic migrations
async def run_migrations() -> bool:
    """Run Alembic migrations to update database schema."""
    import subprocess
    from pathlib import Path
    
    try:
        logger.info("Running Alembic migrations...")
        
        # Get project root
        project_root = Path(__file__).parent.parent.parent
        
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=str(project_root),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Alembic failed: {result.stderr}")
            return False
        
        logger.info("Migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to run migrations: {str(e)}")
        return False


# Initialize database on startup
async def init_db():
    """Initialize database on startup (run migrations + health check)."""
    try:
        # Check database connection with retry
        max_retries = 3
        for attempt in range(max_retries):
            if await check_database_connection():
                break
            if attempt == max_retries - 1:
                raise Exception(f"Database connection failed after {max_retries} attempts")
            logger.warning(f"Database connection attempt {attempt + 1} failed, retrying...")
            await asyncio.sleep(1 * (attempt + 1))

        # Run migrations
        if not await run_migrations():
            raise Exception("Alembic migrations failed!")

        logger.info("Database initialization complete")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
        raise


# Close database on shutdown
async def close_db():
    """Close database connections on shutdown."""
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {str(e)}")