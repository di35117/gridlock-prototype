import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app

pytest_plugins = ('pytest_asyncio',)

@pytest_asyncio.fixture(scope="session")
async def async_client():
    """Creates a virtual HTTP client to test our FastAPI routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client