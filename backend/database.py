from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import DATABASE_URL

# FIX: Massively expanded the pool to survive the Locust swarm without queuing
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=100,         # Increased from 10
    max_overflow=200,      # Increased from 20
    pool_timeout=30,       # Give requests 30 seconds to find a connection before failing
    pool_pre_ping=True,
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