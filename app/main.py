import uuid
import threading
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse  # ← ADD THIS
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded  # ← ADD THIS
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import logger
from app.db.session import create_tables, SessionLocal
from app.db.models import User
from app.api.routes import auth, analysis
from app.services.user_service import UserService
from app.schemas.user import UserCreate
from app.core.security import SecurityService

settings = get_settings()

# ═══════════════════════════════════════════════════════════════
# STARTUP & SHUTDOWN EVENTS
# ═══════════════════════════════════════════════════════════════

async def startup_event():
    """Run on app startup."""
    logger.info("Starting application...#######")
    
    # Create database tables
    create_tables()
    logger.info("Database tables created...######")
    
    # Create dummy user
    create_dummy_user()
    logger.info("Dummy user setup complete...######")


async def shutdown_event():
    """Run on app shutdown."""
    logger.info("Shutting down application...######")


def create_dummy_user():
    """Create dummy user if not exists."""
    db = SessionLocal()
    try:
        # Check if dummy user exists
        dummy_user = db.query(User).filter(User.email == settings.DUMMY_USER_EMAIL).first()
        
        if dummy_user:
            logger.info(f"Dummy user already exists: {settings.DUMMY_USER_EMAIL}")
            return
        
        # Create dummy user
        user_create = UserCreate(
            email=settings.DUMMY_USER_EMAIL,
            full_name=settings.DUMMY_USER_FULL_NAME,
            password=settings.DUMMY_USER_PASSWORD
        )
        
        user = UserService.create_user(db, user_create)
        logger.info(f"Created dummy user: {user.email} (password: {settings.DUMMY_USER_PASSWORD})")
        
    except Exception as e:
        logger.error(f"Failed to create dummy user: {str(e)}")
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# LIFESPAN CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()


# ═══════════════════════════════════════════════════════════════
# CREATE APP
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# ═══════════════════════════════════════════════════════════════
# MIDDLEWARE
# ═══════════════════════════════════════════════════════════════

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# ═══════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════

app.include_router(auth.router)
app.include_router(analysis.router)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": f"Rate limit exceeded: {exc.detail}"}
    )

@app.get("/", tags=["Info"])
def root():
    """API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "endpoints": {
            "Auth": "/api/auth/register, /api/auth/login, /api/auth/me",
            "Analysis": "/api/analysis/analyze, /api/analysis/results/{id}, /api/analysis/history"
        }
    }


@app.get("/health", tags=["Info"])
def health():
    """Health check."""
    return {"status": "healthy"}
