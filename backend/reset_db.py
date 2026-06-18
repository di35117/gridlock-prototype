import asyncio
from sqlalchemy import text
from database import engine

async def drop_incidents():
    print("Connecting to database...")
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS incidents CASCADE;"))
        print("SUCCESS: 'incidents' table dropped!")

if __name__ == "__main__":
    asyncio.run(drop_incidents())