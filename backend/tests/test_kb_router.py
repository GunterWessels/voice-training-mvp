"""Knowledge Base Manager API tests — Task 11."""
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

# Ensure env vars set before import
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-minimum-32-characters-long!!")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("TESTING", "1")


def make_token(payload: dict) -> str:
    from jose import jwt
    secret = os.environ["SUPABASE_JWT_SECRET"]
    return jwt.encode({**payload, "aud": "authenticated"}, secret, algorithm="HS256")


@pytest.fixture
async def anon_client():
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


@pytest.mark.asyncio
async def test_list_chunks_requires_admin(anon_client: AsyncClient):
    """Unauthenticated request must return 401."""
    resp = await anon_client.get("/admin/knowledge-base/tria_stents/chunks")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_add_chunk_validates_domain(admin_client: AsyncClient):
    """Invalid domain value must return 422."""
    # Mock DB so the request gets past auth to validation
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    with patch("routers.knowledge_base.get_db", return_value=mock_db), \
         patch("routers.knowledge_base.embed_text", new_callable=AsyncMock, return_value=[0.1] * 1536), \
         patch("routers.knowledge_base.upsert_chunk", new_callable=AsyncMock):
        resp = await admin_client.post(
            "/admin/knowledge-base/tria_stents/chunks",
            json={
                "domain": "invalid_domain",
                "section": "test",
                "content": "test content",
                "approved_claim": False,
                "keywords": [],
            },
        )
    assert resp.status_code == 422
