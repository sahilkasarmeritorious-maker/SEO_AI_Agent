from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.db.models import User
from app.schemas.user import UserCreate
from app.core.security import SecurityService
from app.core.config import get_settings
from app.services.user_service import UserService

settings = get_settings()


class AuthService:
    @staticmethod
    def register(db: Session, user_data: UserCreate):
        """Register new user."""
        # Check if user exists
        if UserService.get_user_by_email(db, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user = UserService.create_user(db, user_data)
        return user
    
    @staticmethod
    def login(db: Session, email: str, password: str):
        """Login user and return tokens."""
        user = UserService.authenticate_user(db, email, password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User inactive"
            )
        
        # Create tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = SecurityService.create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )
        refresh_token = SecurityService.create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user
        }