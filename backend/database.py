import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import DATABASE_URL

# 1. Read Environment Variables (Defaults to safe local Windows limits)
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 20))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 10))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", 60))

# 2. Check if we are in production using PgBouncer
USE_PGBOUNCER = os.getenv("USE_PGBOUNCER", "false").lower() == "true"

connect_args = {}
if USE_PGBOUNCER:
    # CRITICAL: If using PgBouncer, we must disable asyncpg's statement cache
    connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_pre_ping=True,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)