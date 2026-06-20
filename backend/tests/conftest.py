import pytest
import pytest_asyncio
import os
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from testcontainers.postgres import PostgresContainer
from asgi_lifespan import LifespanManager

postgres = PostgresContainer("postgres:15-alpine")
postgres.start()

test_db_url = postgres.get_connection_url().replace("psycopg2", "asyncpg")
os.environ["DATABASE_URL"] = test_db_url

from main import app
from database import init_db

pytest_plugins = ('pytest_asyncio',)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    await init_db()
    yield
    postgres.stop()

@pytest_asyncio.fixture(scope="session", autouse=True)
def mock_redis():
    with patch('modules.learning_engine.service.redis_client', new_callable=AsyncMock) as mock:
        yield mock

@pytest_asyncio.fixture(scope="session")
async def async_client():
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client