from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User
from app.schemas.user import UserCreate
from app.core.security import SecurityService


class UserService:
    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str):  # async
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))  # await
        return result.scalars().first()
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str):  # async
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))  #  await
        return result.scalars().first()
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int):  #  async
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))  # await
        return result.scalars().first()
    
    @staticmethod
    async def create_user(db: AsyncSession, user: UserCreate):  #  async
        """Create new user."""
        hashed_password = SecurityService.hash_password(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )
        db.add(db_user)
        await db.commit()  #  await
        await db.refresh(db_user)  # await
        return db_user
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, username: str, password: str):  #  async
        """Authenticate user with username and password."""
        user = await UserService.get_user_by_username(db, username)  #  await
        if not user:
            return None
        if not SecurityService.verify_password(password, user.hashed_password):
            return None
        return user