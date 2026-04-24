from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal, init_db, close_db  #  Import async versions
from app.db.models import User
from app.api.routes import auth, analysis
from app.services.user_service import UserService
from app.schemas.user import UserCreate
from app.core.security import SecurityService
from app.services.chroma_service import chroma_service

settings = get_settings()

# ═══════════════════════════════════════════════════════════════
# CREATE DUMMY USER (ASYNC)
# ═══════════════════════════════════════════════════════════════

async def create_dummy_user():
    """Create dummy user if not exists (async version)."""
    async with AsyncSessionLocal() as db:  #  Use async session
        try:
            # Check if dummy user exists
            result = await db.execute(  #  await
                select(User).where(User.username == settings.DUMMY_USER_EMAIL)
            )
            dummy_user = result.scalars().first()
            
            if dummy_user:
                logger.info(f" Dummy user already exists: {settings.DUMMY_USER_EMAIL}")
                return
            
            # Create dummy user
            user_create = UserCreate(
                username=settings.DUMMY_USER_EMAIL,
                email=settings.DUMMY_USER_EMAIL,
                password=settings.DUMMY_USER_PASSWORD
            )
            
            user = await UserService.create_user(db, user_create)  #  await
            logger.info(f" Created dummy user: {user.username}")
            
        except Exception as e:
            logger.error(f" Failed to create dummy user: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# LIFESPAN CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    # ═══ STARTUP ═══
    logger.info(" Starting application...")
    
    try:
        # Initialize database (run migrations)
        await init_db()
        logger.info(" Database initialized")
        
        # Initialize Chroma
        logger.info("🗄️  Initializing Chroma...")
        _ = chroma_service  # Trigger initialization
        logger.info(" Chroma initialized")
        
        # Create dummy user if needed
        await create_dummy_user()
        
        logger.info(" Application startup complete")
    except Exception as e:
        logger.error(f" Startup failed: {str(e)}")
        raise
    
    yield  # App runs here
    
    # ═══ SHUTDOWN ═══
    logger.info(" Shutting down application...")
    try:
        await close_db()
        logger.info(" Application shutdown complete")
    except Exception as e:
        logger.error(f" Shutdown error: {str(e)}")


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
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
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