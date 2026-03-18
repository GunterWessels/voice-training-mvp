"""Admin router tests — Task 1 (admin user management)."""
import os
import io
import sys
import uuid
import pytest
from unittest.mock import AsyncMock, patch

# Set required env vars FIRST, before any backend module imports
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-minimum-32-characters-long!!")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("TESTING", "1")

# Add project root to sys.path so 'backend' is importable as a package
# (models.py uses 'from backend.db import Base')
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# In-memory SQLite test database
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(TEST_DB_URL, echo=False)
_TestSessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False)

# Raw DDL for the users table in SQLite (mirrors models.py User fields we need)
_CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    role TEXT NOT NULL DEFAULT 'rep',
    cohort_id TEXT,
    division_id TEXT,
    created_at TEXT,
    last_active_at TEXT
)
"""


async def _create_tables():
    async with _test_engine.begin() as conn:
        await conn.execute(_create_users_sql_text())


def _create_users_sql_text():
    from sqlalchemy import text
    return text(_CREATE_USERS_SQL)


# ---------------------------------------------------------------------------
# Dependency overrides
# ---------------------------------------------------------------------------

ADMIN_USER = {"user_id": str(uuid.uuid4()), "email": "admin@test.com", "role": "admin"}


async def _override_get_admin_user():
    """Bypass DB lookup — always returns a valid admin."""
    return ADMIN_USER


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
async def setup_test_db():
    """Create SQLite tables once for the module."""
    await _create_tables()
    yield
    await _test_engine.dispose()


@pytest.fixture
async def admin_ac():
    """AsyncClient with admin dependency override and SQLite session override."""
    from main import app
    from routers.admin import get_admin_user

    app.dependency_overrides[get_admin_user] = _override_get_admin_user

    with patch("routers.admin.AsyncSessionLocal", _TestSessionLocal):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.pop(get_admin_user, None)


@pytest.fixture
async def anon_ac():
    """AsyncClient with no auth headers."""
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _csv_bytes(rows: list) -> bytes:
    """Build minimal CSV bytes from a list of dicts."""
    if not rows:
        return b""
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(str(row.get(h, "")) for h in headers))
    return "\n".join(lines).encode()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_users_returns_list(admin_ac: AsyncClient):
    """GET /api/admin/users returns a list (possibly empty)."""
    resp = await admin_ac.get("/api/admin/users")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_user_returns_201(admin_ac: AsyncClient):
    """POST /api/admin/users creates a user and returns 201."""
    with patch("routers.admin._invite_user", new=AsyncMock()):
        resp = await admin_ac.post("/api/admin/users", json={
            "email": "newrep@example.com",
            "first_name": "New",
            "last_name": "Rep",
            "role": "rep",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newrep@example.com"
    assert data["first_name"] == "New"
    assert data["role"] == "rep"
    assert "id" in data


@pytest.mark.asyncio
async def test_duplicate_email_returns_409(admin_ac: AsyncClient):
    """Second POST with same email returns 409."""
    payload = {
        "email": "duplicate@example.com",
        "first_name": "Dupe",
        "last_name": "User",
        "role": "rep",
    }
    with patch("routers.admin._invite_user", new=AsyncMock()):
        r1 = await admin_ac.post("/api/admin/users", json=payload)
        assert r1.status_code == 201

        r2 = await admin_ac.post("/api/admin/users", json=payload)
        assert r2.status_code == 409


@pytest.mark.asyncio
async def test_delete_user_returns_204(admin_ac: AsyncClient):
    """DELETE /api/admin/users/{id} returns 204."""
    with patch("routers.admin._invite_user", new=AsyncMock()):
        create_resp = await admin_ac.post("/api/admin/users", json={
            "email": "todelete@example.com",
            "first_name": "Del",
            "last_name": "Me",
            "role": "rep",
        })
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    del_resp = await admin_ac.delete(f"/api/admin/users/{user_id}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent_user_returns_404(admin_ac: AsyncClient):
    """DELETE for unknown user_id returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await admin_ac.delete(f"/api/admin/users/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_parse_upload_detects_csv_columns(admin_ac: AsyncClient):
    """parse-upload correctly detects standard CSV headers."""
    csv_content = _csv_bytes([
        {"email": "a@b.com", "first_name": "Alice", "last_name": "Smith"},
    ])
    resp = await admin_ac.post(
        "/api/admin/users/parse-upload",
        files={"file": ("users.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected"].get("email") == "email"
    assert data["detected"].get("first_name") == "first_name"
    assert data["detected"].get("last_name") == "last_name"
    assert data["total_rows"] == 1


@pytest.mark.asyncio
async def test_parse_upload_fuzzy_headers(admin_ac: AsyncClient):
    """parse-upload handles fuzzy headers like 'e-mail' and 'full name'."""
    csv_content = _csv_bytes([
        {"e-mail": "x@y.com", "full name": "Bob Jones"},
    ])
    resp = await admin_ac.post(
        "/api/admin/users/parse-upload",
        files={"file": ("users.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected"].get("email") == "e-mail"
    assert data["detected"].get("name") == "full name"


@pytest.mark.asyncio
async def test_unauthenticated_list_returns_401(anon_ac: AsyncClient):
    """GET /api/admin/users without auth returns 401."""
    resp = await anon_ac.get("/api/admin/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_user(admin_ac: AsyncClient):
    """PUT /api/admin/users/{id} updates fields and returns updated user."""
    with patch("routers.admin._invite_user", new=AsyncMock()):
        create_resp = await admin_ac.post("/api/admin/users", json={
            "email": "toupdate@example.com",
            "first_name": "Old",
            "last_name": "Name",
            "role": "rep",
        })
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    update_resp = await admin_ac.put(f"/api/admin/users/{user_id}", json={
        "first_name": "Updated",
        "role": "admin",
    })
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["first_name"] == "Updated"
    assert data["role"] == "admin"
