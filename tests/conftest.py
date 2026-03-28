# tests/conftest.py
import pytest
import pytest_asyncio
import os
import sys
from jose import jwt
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://localhost/voice_training_test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-at-least-32-chars-long!!")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-el-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("TESTING", "1")

# Add backend dir to sys.path so all intra-backend imports resolve via short path.
# IMPORTANT: import `main`, `models`, `db` WITHOUT the `backend.` prefix everywhere
# in this conftest and in tests/ — mixing prefixes causes SQLAlchemy double-registration.
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, os.path.abspath(_backend_dir))

from main import app  # short path — consistent with sys.path.insert above

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest_asyncio.fixture
async def async_client():
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
def valid_jwt():
    return jwt.encode(
        {"sub": "user-uuid-123", "email": "rep@bsci.com", "role": "rep",
         "aud": "authenticated", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256"
    )

@pytest.fixture
def expired_jwt():
    return jwt.encode(
        {"sub": "user-uuid-123", "aud": "authenticated",
         "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256"
    )

@pytest_asyncio.fixture
async def seeded_scenario():
    """Insert a minimal test scenario and return its UUID."""
    from db import AsyncSessionLocal
    from models import Scenario, Division
    import uuid
    async with AsyncSessionLocal() as db:
        div = Division(name="Test Division", slug=f"test-{uuid.uuid4().hex[:8]}")
        db.add(div)
        await db.flush()
        scenario = Scenario(
            name="Test Scenario",
            division_id=div.id,
            product_name="Test Product",
            persona_id="vac_buyer",
            arc={"stages": [
                {"id": 1, "name": "DISCOVERY",
                 "persona_instruction": "Be vague.",
                 "unlock_condition": "open_ended_questions >= 2",
                 "max_turns": 6}
            ]},
        )
        db.add(scenario)
        await db.commit()
        yield {"scenario_id": str(scenario.id), "division_id": str(div.id)}

@pytest_asyncio.fixture
async def tria_scenario_id(seeded_scenario):
    return seeded_scenario["scenario_id"]

@pytest_asyncio.fixture
async def seeded_metering_session():
    """Insert a minimal User + Session + 3 MeteringEvents totaling $0.045."""
    from db import AsyncSessionLocal
    from models import Division, Scenario, User, Session, MeteringEvent
    import uuid
    async with AsyncSessionLocal() as db:
        div = Division(name="Metering Test Division", slug=f"metering-{uuid.uuid4().hex[:8]}")
        db.add(div)
        await db.flush()
        scenario = Scenario(
            division_id=div.id, name="Metering Test Scenario",
            persona_id="vac_buyer",
            product_name="Test Product",
            arc={"stages": []},
        )
        db.add(scenario)
        await db.flush()
        user = User(
            id=uuid.uuid4(),
            email=f"meter-{uuid.uuid4().hex[:6]}@bsci.com",
            first_name="Meter", last_name="Rep", role="rep"
        )
        db.add(user)
        await db.flush()
        session = Session(
            user_id=user.id, scenario_id=scenario.id,
            preset="full_practice", status="completed"
        )
        db.add(session)
        await db.flush()
        for cost in [0.015, 0.015, 0.015]:
            db.add(MeteringEvent(
                session_id=session.id, user_id=user.id,
                provider="openai", model="gpt-4o-mini", call_type="persona_response",
                tokens_in=100, tokens_out=50, cost_usd=cost,
            ))
        await db.commit()
        yield str(session.id)
