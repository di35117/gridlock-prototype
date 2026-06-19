import pytest
import pytest_asyncio
import os
from httpx import AsyncClient, ASGITransport
from testcontainers.postgres import PostgresContainer

# 1. SPIN UP THE VIRTUAL DATABASE (Before FastAPI imports)
# This downloads a temporary Postgres image and boots it up
postgres = PostgresContainer("postgres:15-alpine")
postgres.start()

# 2. HIJACK THE ENVIRONMENT VARIABLE
# We force SQLAlchemy to use our temporary DB instead of your real one,
# and we replace standard psycopg2 with the asyncpg driver your app uses.
test_db_url = postgres.get_connection_url().replace("psycopg2", "asyncpg")
os.environ["DATABASE_URL"] = test_db_url

# Now it is safe to import your app, because DATABASE_URL is hijacked
from main import app
from database import init_db

pytest_plugins = ('pytest_asyncio',)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """
    Creates the tables in the temporary database, 
    yields to let the tests run, and then cleans up.
    """
    await init_db()
    yield
    # Stop and destroy the container when tests finish
    postgres.stop()

@pytest_asyncio.fixture(scope="session")
async def async_client():
    """Virtual async client to test FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client