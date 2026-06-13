"""
Kwork AI PM - Authentication Service
"""
from datetime import datetime, timedelta
from typing import Optional
import bcrypt as _bcrypt
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from config import settings
from models.user import User


class AuthService:
    """Authentication service for JWT token management"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return _bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash"""
        return _bcrypt.hashpw(
            password.encode("utf-8"),
            _bcrypt.gensalt(),
        ).decode("utf-8")
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password"""
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        if not AuthService.verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """Get user by username"""
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user(
        db: AsyncSession, 
        username: str, 
        email: str, 
        password: str,
        is_admin: bool = False
    ) -> User:
        """Create new user"""
        # Check if user exists
        existing = await AuthService.get_user_by_username(db, username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        user = User(
            username=username,
            email=email,
            password_hash=AuthService.get_password_hash(password),
            is_admin=is_admin,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def create_default_admin(db: AsyncSession):
        """Create default admin user if not exists"""
        existing = await AuthService.get_user_by_username(db, settings.DEFAULT_ADMIN_USERNAME)
        if not existing:
            await AuthService.create_user(
                db,
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                password=settings.DEFAULT_ADMIN_PASSWORD,
                is_admin=True
            )
            print(f"✅ Default admin user created: {settings.DEFAULT_ADMIN_USERNAME}")
