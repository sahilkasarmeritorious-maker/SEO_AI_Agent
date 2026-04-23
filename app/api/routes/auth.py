from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession  # Change this
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.db.session import get_db
from app.schemas.user import UserCreate, Token, UserResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.core.security import get_current_user
from app.core.logging import logger

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(  # Make async
    request: Request, 
    user_data: UserCreate, 
    db: AsyncSession = Depends(get_db)  # Change Session → AsyncSession
):
    """Register new user."""
    logger.info(f"User registration attempt: {user_data.email}")
    user = await AuthService.register(db, user_data)  # Add await
    logger.info(f"User registered: {user.email}")
    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(  # Make async
    request: Request, 
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)  # Change Session → AsyncSession
):
    """Login user and get tokens. Compatible with Swagger UI Authorize button."""
    logger.info(f"Login attempt: {form_data.username}")
    
    # Use username field (which is the email in our case)
    result = await AuthService.login(db, form_data.username, form_data.password)  # Add await
    logger.info(f"User logged in: {form_data.username}")
    return result


@router.get("/me", response_model=UserResponse)
@limiter.limit("30/minute")
async def get_current_user_info(  # Make async
    request: Request, 
    current_user_id: int = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)  # Change Session → AsyncSession
):
    """Get current user info."""
    user = await UserService.get_user_by_id(db, current_user_id)  #  Add await
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user