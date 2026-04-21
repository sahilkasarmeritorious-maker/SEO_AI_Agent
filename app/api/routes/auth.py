from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
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
def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user."""
    logger.info(f"User registration attempt: {user_data.email}")
    user = AuthService.register(db, user_data)
    logger.info(f"User registered: {user.email}")
    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login user and get tokens. Compatible with Swagger UI Authorize button."""
    logger.info(f"Login attempt: {form_data.username}")
    
    # Use username field (which is the email in our case)
    result = AuthService.login(db, form_data.username, form_data.password)
    logger.info(f"User logged in: {form_data.username}")
    return result


@router.get("/me", response_model=UserResponse)
@limiter.limit("30/minute")
def get_current_user_info(request: Request, current_user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user info."""
    user = UserService.get_user_by_id(db, current_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user