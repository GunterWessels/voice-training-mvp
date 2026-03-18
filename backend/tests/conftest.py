import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Set required env vars before any backend module imports
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-minimum-32-characters-long!!")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("TESTING", "1")


def make_token(payload: dict) -> str:
    """Create a signed JWT using the test secret."""
    from jose import jwt
    secret = os.environ["SUPABASE_JWT_SECRET"]
    return jwt.encode({**payload, "aud": "authenticated"}, secret, algorithm="HS256")


@pytest.fixture
def client():
    """Unauthenticated test client."""
    from main import app
    from httpx import ASGITransport, AsyncClient
    # Return a sync-compatible object for use in async tests via the async_client fixture
    return None  # placeholder — tests use admin_client or direct AsyncClient


@pytest.fixture
async def async_client():
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_client():
    from main import app
    token = make_token({"sub": "admin-user-id", "role": "admin"})
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac
