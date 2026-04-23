from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.db.models import User
from app.schemas.user import UserCreate
from app.core.security import SecurityService
from app.core.config import get_settings
from app.services.user_service import UserService

settings = get_settings()


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, user_data: UserCreate):  # async
        """Register new user."""
        # Check if username exists
        existing_user = await UserService.get_user_by_username(db, user_data.username)  # await
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email exists
        existing_email = await UserService.get_user_by_email(db, user_data.email)  # await
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user = await UserService.create_user(db, user_data)  #  await
        return user
    
    @staticmethod
    async def login(db: AsyncSession, username: str, password: str):  #  async
        """Login user and return tokens."""
        user = await UserService.authenticate_user(db, username, password)  #  await
        
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
            "token_type": "bearer",
            "user": user
        }