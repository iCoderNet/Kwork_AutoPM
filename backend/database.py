"""
Kwork AI Project Manager - Database Configuration
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from config import settings
import os

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    # aiosqlite + SQLite: timeout orqali "database is locked" ni bartaraf etish
    connect_args={"timeout": 30},
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency for getting database session"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # WAL mode — concurrent read/write, lock muammosi yo'q
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous=NORMAL"))
        await conn.execute(text("PRAGMA busy_timeout=30000"))  # 30s
        await conn.run_sync(Base.metadata.create_all)
