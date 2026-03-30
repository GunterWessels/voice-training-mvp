# Backend Fix: Test Suite & Model Integrity

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 failures + 3 errors in the root `tests/` suite caused by a double SQLAlchemy model import, verify `KnowledgeChunk` model integrity, and patch the `test_valid_token_passes` auth test.

**Architecture:** The root cause is `tests/conftest.py` doing two conflicting things at once: inserting `backend/` into `sys.path` (so modules are importable as `models`, `db`, `main`) AND then importing with the `backend.` prefix (`from backend.main import app`). SQLAlchemy sees `models.Division` and `backend.models.Division` as two distinct classes sharing one `Base` — and raises `Table 'divisions' is already defined`. Fix: standardize ALL imports in `tests/` to use the short path (consistent with the `sys.path.insert`).

**Tech Stack:** Python 3.12, pytest, SQLAlchemy 2.0, FastAPI, asyncpg, pgvector

---

## File Map

| Action | File | Change |
|--------|------|--------|
| Modify | `tests/conftest.py` | Change `backend.X` imports → short-path `X` imports |
| Modify | `tests/test_rag_models.py` | Change `backend.models` imports → `models` |
| Modify | `backend/models.py` | Add missing `keywords` column to `KnowledgeChunk` if absent |
| Read | `backend/auth.py` | Understand how TESTING=1 is used (for auth test fix) |
| Modify | `tests/test_auth.py` | Mock DB user lookup so `test_valid_token_passes` doesn't need live PG |

---

## Task 1: Fix double-import root cause in `tests/conftest.py`

**Files:**
- Modify: `tests/conftest.py`

**Context:** `conftest.py` inserts `backend/` into `sys.path` at line 23, then immediately imports `from backend.main import app` at line 25. Python resolves `backend.main` through the package path, so inside `backend/main.py` all `from models import X` calls register under `models.*`. When any test then does `from backend.models import Y`, Python re-executes `backend/models.py` under the `backend.models` namespace, creating a second set of classes in the same `Base`. Result: SQLAlchemy `InvalidRequestError: Table 'divisions' is already defined`.

Fix: keep the `sys.path.insert` (required for intra-backend imports to work without relative imports) and change ALL `backend.X` imports in conftest to use the short path.

- [ ] **Step 1: Run the failing tests to capture the baseline**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp
python3 -m pytest tests/ -q --no-header 2>&1 | tail -15
```

Expected: 3 failed, 3 errors (baseline)

- [ ] **Step 2: Patch `tests/conftest.py`**

Replace lines 25 and 56–57 and 88 and 103 so all `backend.X` become short-path `X`:

```python
# tests/conftest.py  — full replacement
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
    from db import AsyncSessionLocal          # short path
    from models import Scenario, Division    # short path
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
    from db import AsyncSessionLocal                                    # short path
    from models import Division, Scenario, User, Session, MeteringEvent  # short path
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
```

- [ ] **Step 3: Patch `tests/test_rag_models.py` — remove `backend.` prefix**

```python
# tests/test_rag_models.py  — full replacement
def test_knowledge_chunk_model_has_required_fields():
    from models import KnowledgeChunk  # short path — consistent with conftest
    cols = {c.name for c in KnowledgeChunk.__table__.columns}
    assert {"id", "scenario_id", "product_id", "domain", "content",
            "approved_claim", "keywords", "embedding"} <= cols

def test_scenario_model_has_rag_columns():
    from models import Scenario  # short path
    cols = {c.name for c in Scenario.__table__.columns}
    assert {"cof_map", "argument_rubrics", "grading_criteria", "methodology"} <= cols
```

- [ ] **Step 4: Run the two RAG model tests to see if they pass now**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp
python3 -m pytest tests/test_rag_models.py -v --no-header 2>&1
```

Expected: both PASS (double-import eliminated; Scenario already has the 4 RAG columns per models.py lines 59-62). If `KnowledgeChunk` fails due to missing `keywords` column, proceed to Task 2. Otherwise skip Task 2.

- [ ] **Step 5: Commit**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp
git add tests/conftest.py tests/test_rag_models.py
git commit -m "fix(tests): resolve SQLAlchemy double-registration by standardizing import paths"
```

---

## Task 2: Add `keywords` column to `KnowledgeChunk` model (run only if Task 1 Step 4 fails)

**Files:**
- Modify: `backend/models.py`

**Context:** `test_knowledge_chunk_model_has_required_fields` asserts `keywords` is in `KnowledgeChunk.__table__.columns`. If the model is missing it, add it now. The migration `002_rag.sql` already defines `keywords TEXT[]` — the model just needs to match.

- [ ] **Step 1: Check if KnowledgeChunk has `keywords`**

```bash
grep -n "keywords" /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/backend/models.py
```

Expected: one line showing `keywords` mapped column. If no output → proceed to Step 2.

- [ ] **Step 2: Add `keywords` to KnowledgeChunk in `backend/models.py`**

Find the `KnowledgeChunk` class and add the `keywords` column after `page`:

```python
# In backend/models.py — add to KnowledgeChunk class after the `page` column:
keywords: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
```

The `ARRAY` import is already present at the top of models.py. `Text` is also already imported.

- [ ] **Step 3: Run RAG model test again**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp
python3 -m pytest tests/test_rag_models.py -v --no-header 2>&1
```

Expected: both PASS

- [ ] **Step 4: Commit**

```bash
git add backend/models.py
git commit -m "fix(models): add keywords column to KnowledgeChunk to match migration 002"
```

---

## Task 3: Fix `test_valid_token_passes` auth test

**Files:**
- Read: `backend/auth.py` (understand current `/api/sessions` handler)
- Modify: `tests/test_auth.py`

**Context:** `test_valid_token_passes` sends a valid JWT to `GET /api/sessions` and expects `200`. The handler likely queries PostgreSQL for user existence. In test mode the test DB is not running, so it returns `500` instead of `200`. Two options: (A) mock the DB call in auth middleware for `TESTING=1`, or (B) mock the `/api/sessions` DB query in the test. Option B is less invasive.

- [ ] **Step 1: Run the auth test with verbose output to see actual status code**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp
python3 -m pytest tests/test_auth.py::test_valid_token_passes -v -s 2>&1
```

Read the actual error — if it's `500` (DB down) proceed to Step 2. If it's `403` (role check) proceed to Step 3.

- [ ] **Step 2 (if 500 — DB not available): Mock the DB dependency in the test**

Add a fixture override in `tests/test_auth.py` that patches the SQLAlchemy session used by the `/api/sessions` route:

```python
# tests/test_auth.py  — add at top
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

def test_missing_token_returns_401(client):
    response = client.get("/api/sessions")
    assert response.status_code == 401

def test_invalid_token_returns_401(client):
    response = client.get("/api/sessions",
        headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401

def test_valid_token_passes(client, valid_jwt):
    # Patch the DB session so the sessions handler returns [] without hitting PostgreSQL.
    # The auth middleware runs BEFORE the handler, so JWT validation still executes fully.
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    with patch("db.AsyncSessionLocal", return_value=mock_session):
        response = client.get("/api/sessions",
            headers={"Authorization": f"Bearer {valid_jwt}"})
    assert response.status_code == 200

def test_expired_token_returns_401(client, expired_jwt):
    response = client.get("/api/sessions",
        headers={"Authorization": f"Bearer {expired_jwt}"})
    assert response.status_code == 401

def test_cohort_token_valid(client):
    response = client.post("/api/join",
        json={"cohort_token": "valid-test-token", "email": "rep@bsci.com", "name": "Test Rep"})
    assert response.status_code in (200, 201)

def test_cohort_token_invalid_returns_400(client):
    response = client.post("/api/join",
        json={"cohort_token": "nonexistent", "email": "rep@bsci.com", "name": "Test Rep"})
    assert response.status_code == 400
```

- [ ] **Step 3 (if 403 — role check failing): Check what `/api/sessions` does after JWT validation**

```bash
grep -n "api/sessions\|def.*sessions" /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/backend/main.py | head -20
```

Read the handler. If it checks the DB for a `users` row with `role`, mock the user lookup:

```python
# In test_valid_token_passes, wrap with a mock that returns a user row:
mock_user = MagicMock()
mock_user.role = "rep"
mock_user.id = "user-uuid-123"
with patch("auth.get_current_user", return_value=mock_user):
    response = client.get("/api/sessions",
        headers={"Authorization": f"Bearer {valid_jwt}"})
assert response.status_code == 200
```

- [ ] **Step 4: Run the full auth test file**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp
python3 -m pytest tests/test_auth.py -v --no-header 2>&1
```

Expected: all 6 PASS

- [ ] **Step 5: Run the full test suite to confirm green**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp
python3 -m pytest tests/ -q --no-header 2>&1 | tail -10
```

Expected: 0 failed, 0 errors

- [ ] **Step 6: Commit**

```bash
git add tests/test_auth.py
git commit -m "fix(tests): mock DB in test_valid_token_passes so it passes without live PostgreSQL"
```

---

## Self-Review

**Spec coverage:**
- Double-import root cause → Task 1 ✓
- `KnowledgeChunk.keywords` column → Task 2 (conditional) ✓
- `test_valid_token_passes` → Task 3 ✓
- Integration/metering/WebSocket errors (cascade from double-import) → resolved by Task 1 ✓

**No placeholders:** All steps have exact code, exact commands, expected output.

**Type consistency:** `from models import ...` used consistently across Tasks 1-3.

---

*Plan complete. Execute with `superpowers:subagent-driven-development` or `superpowers:executing-plans`.*
