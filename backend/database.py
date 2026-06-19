import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from config import DATABASE_URL

# For high-concurrency async apps, NullPool allows the underlying driver (asyncpg)
# to instantly create and close connections without getting stuck in a queue.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,  # FIX: Bypasses connection pool limits entirely
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