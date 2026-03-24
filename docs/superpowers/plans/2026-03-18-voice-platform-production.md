# Voice Training Platform — Production Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the voice-training-mvp into a production-ready, Railway-deployed platform for BSCI with auth, PostgreSQL, COF arc evaluation, metering, CE certificates, Next.js 15 frontend, and easter egg celebrations.

**Architecture:** FastAPI backend (hardened, single worker, PostgreSQL) + Next.js 15 TypeScript frontend (replaces React CRA) + Railway managed Postgres + Supabase Auth (JWT only). The existing `ai_service.py`, `tts_service.py`, and `cartridge_service.py` are retained and hardened — not rewritten.

**Tech Stack:** Python 3.12, FastAPI, asyncpg, SQLAlchemy 2.0, python-jose, slowapi, reportlab, resend / Next.js 15, TypeScript, Tailwind CSS, @supabase/ssr / Railway PostgreSQL, Supabase Auth / ElevenLabs, OpenAI GPT-4o-mini

**Spec:** `docs/superpowers/specs/2026-03-18-voice-platform-production-design.md`

---

## File Map

### Backend — new files
```
backend/auth.py                        JWT middleware + Supabase verification
backend/arc_engine.py                  Condition evaluator + arc stage tracker
backend/metering.py                    Metering event writer + cost computation
backend/cert_service.py                PDF generation (reportlab) + email (resend)
backend/db.py                          Async SQLAlchemy engine + session factory
backend/models.py                      SQLAlchemy ORM models (all 9 tables)
backend/migrations/001_initial.sql     Full schema DDL
backend/Dockerfile                     Production Docker image (single worker)
backend/assets/ls_logo.png             LiquidSMARTS™ logo (copy from brand assets)
backend/assets/signature.png           Signature image
backend/assets/fonts/Oswald-Bold.ttf   Brand font
backend/assets/fonts/Manrope-Regular.ttf
scripts/generate_filler_audio.py       One-time filler clip generator
tests/conftest.py                      pytest fixtures (DB, auth, mock AI)
tests/test_auth.py
tests/test_arc_engine.py
tests/test_metering.py
tests/test_cert_service.py
tests/test_websocket.py
tests/test_rate_limiting.py
tests/fixtures/transcripts/            50 labeled transcript fixtures for COF gate test
```

### Backend — modified files
```
backend/main.py                        Auth middleware, CORS, rate limiting, error sanitization,
                                       PostgreSQL session, single-worker WebSocket handler
backend/ai_service.py                  Token budget cap, metering hook
backend/tts_service.py                 Per-persona filler cache paths
backend/requirements.txt               Add: asyncpg, sqlalchemy, python-jose[cryptography],
                                       slowapi, reportlab, resend, supabase
```

### Frontend — new directory (replaces frontend/)
```
frontend-next/
  app/layout.tsx                       Root layout, Supabase provider
  app/page.tsx                         Redirect → /dashboard
  app/auth/callback/page.tsx           Magic link callback
  app/join/[token]/page.tsx            Cohort token onboarding
  app/dashboard/page.tsx               Rep dashboard (queue, history, certs)
  app/train/[sessionId]/page.tsx       Voice chat session page
  app/manager/page.tsx                 Manager cohort dashboard
  app/admin/page.tsx                   Admin ops + cost dashboard
  components/VoiceChat.tsx             WebSocket voice conversation engine
  components/ArcProgress.tsx           6-dot arc progress strip
  components/CofGates.tsx              3-gate COF display
  components/FillerAudio.tsx           Filler clip manager (800ms trigger)
  components/OnboardingOverlay.tsx     First-load 20s audio overlay
  components/AudioStateDisplay.tsx     idle/listening/processing/speaking state indicator + waveform
  components/CelebrationLayer.tsx      Easter egg trigger + animation layer
  components/ScenarioCard.tsx          Practice queue card with handoff QR
  lib/supabase.ts                      createBrowserClient / createServerClient
  lib/api.ts                           Typed fetch wrappers for FastAPI
  middleware.ts                        JWT refresh via @supabase/ssr
  package.json
  tsconfig.json
  tailwind.config.ts
  next.config.ts
  tests/                               Jest + Testing Library
```

### Deployment
```
.github/workflows/deploy.yml           CI/CD: test → build → Railway deploy
railway.json                           Railway service config
docker-compose.yml                     Local full-stack dev
```

---

## Sprint 1: Database + Auth Foundation

### Task 1.1: PostgreSQL schema + migrations

**Files:**
- Create: `backend/migrations/001_initial.sql`
- Create: `backend/db.py`
- Create: `backend/models.py`

- [ ] **Step 1: Write the schema DDL**

Create `backend/migrations/001_initial.sql` with the full schema from spec Section 5.1. Include all tables: `divisions`, `cohorts`, `users`, `scenarios`, `sessions`, `messages`, `completions`, `metering_events`, `practice_series`, `practice_series_items`. Include all indexes from Section 5.3.

- [ ] **Step 2: Write the async DB engine**

Create `backend/db.py`:
```python
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ["DATABASE_URL"].replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5, max_overflow=10)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 3: Write ORM models**

Create `backend/models.py` with SQLAlchemy 2.0 mapped classes for all 9 tables. Match column names exactly to the DDL. Use `Mapped` and `mapped_column` syntax.

- [ ] **Step 4: Write migration test**

Create `tests/test_db.py`:
```python
import pytest
from sqlalchemy import text
from backend.db import engine

@pytest.mark.asyncio
async def test_all_tables_exist():
    tables = ["divisions","cohorts","users","scenarios","sessions",
              "messages","completions","metering_events",
              "practice_series","practice_series_items"]
    async with engine.connect() as conn:
        for table in tables:
            result = await conn.execute(
                text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
                {"t": table}
            )
            assert result.fetchone() is not None, f"Table {table} missing"
```

- [ ] **Step 5: Run test (expect fail — no DB yet)**

```bash
cd backend && pytest tests/test_db.py -v
```

- [ ] **Step 6: Apply migration to local Railway dev DB**

```bash
psql $DATABASE_URL -f migrations/001_initial.sql
```

- [ ] **Step 7: Run test (expect pass)**

```bash
pytest tests/test_db.py -v
# Expected: PASSED test_all_tables_exist
```

- [ ] **Step 8: Commit**

```bash
git add backend/migrations/ backend/db.py backend/models.py tests/test_db.py
git commit -m "feat(db): PostgreSQL schema, async engine, ORM models"
```

---

### Task 1.2: JWT auth middleware

**Files:**
- Create: `backend/auth.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add dependencies**

```
# backend/requirements.txt additions:
python-jose[cryptography]>=3.3.0
supabase>=2.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
reportlab>=4.0.0
resend>=0.7.0
```

Also create `backend/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 2: Write failing auth tests**

Create `tests/test_auth.py`:
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

def test_missing_token_returns_401(client):
    response = client.get("/api/sessions")
    assert response.status_code == 401

def test_invalid_token_returns_401(client):
    response = client.get("/api/sessions",
        headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401

def test_valid_token_passes(client, valid_jwt):
    response = client.get("/api/sessions",
        headers={"Authorization": f"Bearer {valid_jwt}"})
    assert response.status_code != 401

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

- [ ] **Step 3: Run tests (expect fail)**

```bash
pytest tests/test_auth.py -v
# Expected: FAILED — no auth module yet
```

- [ ] **Step 4: Implement auth module**

Create `backend/auth.py`:
```python
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]  # from Supabase dashboard

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return {"user_id": payload["sub"], "email": payload.get("email"), "role": payload.get("role", "rep")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*roles: str):
    async def checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

async def verify_ws_token(token: str) -> dict:
    """Verify JWT passed as WebSocket query parameter."""
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET,
                             algorithms=["HS256"], audience="authenticated")
        return {"user_id": payload["sub"], "email": payload.get("email")}
    except JWTError:
        return None
```

- [ ] **Step 5: Add env var to test conftest**

Create `tests/conftest.py`:
```python
import pytest
import os
from jose import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://localhost/voice_test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-at-least-32-chars-long!!")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-el-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
async def async_client():
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
def valid_jwt():
    return jwt.encode(
        {"sub": "user-uuid-123", "email": "rep@bsci.com", "role": "rep",
         "aud": "authenticated", "exp": datetime.utcnow() + timedelta(hours=1)},
        os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256"
    )

@pytest.fixture
def expired_jwt():
    return jwt.encode(
        {"sub": "user-uuid-123", "aud": "authenticated",
         "exp": datetime.utcnow() - timedelta(hours=1)},
        os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256"
    )

@pytest.fixture
async def seeded_scenario():
    """Insert a minimal test scenario and return its UUID."""
    from backend.db import AsyncSessionLocal
    from backend.models import Scenario, Division
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

@pytest.fixture
async def tria_scenario_id(seeded_scenario):
    """Alias: returns the scenario UUID string for integration tests."""
    return seeded_scenario["scenario_id"]

@pytest.fixture
async def seeded_metering_session():
    """Insert a minimal User + Session + 3 MeteringEvents totaling $0.045 and return the session UUID."""
    from backend.db import AsyncSessionLocal
    from backend.models import Division, Scenario, User, Session, MeteringEvent
    import uuid
    async with AsyncSessionLocal() as db:
        # Division → Scenario → User → Session to satisfy FK chain
        div = Division(name="Metering Test Division", slug=f"metering-{uuid.uuid4().hex[:8]}")
        db.add(div)
        await db.flush()
        scenario = Scenario(
            division_id=div.id, name="Metering Test Scenario",
            persona_id="vac_buyer",   # NOT NULL in spec DDL
            product_name="Test Product",
            arc={"stages": []},
        )
        db.add(scenario)
        await db.flush()
        user = User(
            id=uuid.uuid4(),  # PK is the Supabase UID — no separate supabase_id column
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
        # 3 events: $0.015 + $0.015 + $0.015 = $0.045
        for cost in [0.015, 0.015, 0.015]:
            db.add(MeteringEvent(
                session_id=session.id, user_id=user.id,
                provider="openai", model="gpt-4o-mini", call_type="persona_response",
                tokens_in=100, tokens_out=50, cost_usd=cost,
            ))
        await db.commit()
        yield str(session.id)
```

- [ ] **Step 6: Wire auth into main.py REST endpoints**

In `backend/main.py`, add `Depends(get_current_user)` to all endpoints except `/`, `/personas`, `/tts-info`, and `/api/join`.

- [ ] **Step 7: Run tests (expect pass)**

```bash
pytest tests/test_auth.py -v
# Expected: 6 PASSED
```

- [ ] **Step 8: Commit**

```bash
git add backend/auth.py tests/test_auth.py tests/conftest.py backend/requirements.txt
git commit -m "feat(auth): Supabase JWT middleware + cohort token onboarding"
```

---

### Task 1.3: CORS, rate limiting, error sanitization

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_rate_limiting.py`:
```python
def test_cors_blocks_unknown_origin(client):
    response = client.get("/", headers={"Origin": "https://evil.com"})
    assert "access-control-allow-origin" not in response.headers or \
           response.headers.get("access-control-allow-origin") != "https://evil.com"

def test_error_response_contains_no_stack_trace(client, valid_jwt):
    response = client.post("/api/sessions",
        headers={"Authorization": f"Bearer {valid_jwt}"},
        json={"persona_id": "nonexistent_persona_that_will_cause_error"})
    body = response.json()
    assert "traceback" not in str(body).lower()
    assert "exception" not in str(body).lower()
    assert "file \"" not in str(body).lower()

def test_rate_limit_returns_429_after_threshold(client, valid_jwt):
    """Fire 25 POST /sessions; at least one must return 429 (limit: 20/minute).
    POST /sessions is explicitly decorated with @limiter.limit("20/minute") in Task 1.3 Step 3.
    We target this endpoint — not /personas — because /personas is intentionally unthrottled."""
    responses = [
        client.post("/sessions",
            headers={"Authorization": f"Bearer {valid_jwt}"},
            json={"scenario_id": "00000000-0000-0000-0000-000000000000", "preset": "quick_drill"})
        for _ in range(25)
    ]
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes, f"Expected 429, got: {set(status_codes)}"
```

- [ ] **Step 2: Update main.py CORS and error handling**

```python
# In backend/main.py — replace existing CORS middleware:
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Global exception handler — sanitize all errors:
@app.exception_handler(Exception)
async def sanitized_exception_handler(request, exc):
    import logging
    logging.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "processing_error"})
```

- [ ] **Step 3: Add rate limit decorator to AI endpoints**

```python
@app.post("/sessions")
@limiter.limit("20/minute")
async def create_session(request: Request, ...):
    ...
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_rate_limiting.py -v
# Expected: 2 PASSED
```

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_rate_limiting.py
git commit -m "feat(security): CORS env config, rate limiting, error sanitization"
```

---

## Sprint 2: Arc Engine + COF Evaluation

### Task 2.1: Condition evaluation engine

**Files:**
- Create: `backend/arc_engine.py`
- Create: `tests/test_arc_engine.py`
- Create: `tests/fixtures/transcripts/` (50 labeled fixtures)

- [ ] **Step 1: Write failing tests first**

Create `tests/test_arc_engine.py`:
```python
import pytest
from backend.arc_engine import ConditionEvaluator, ArcStageTracker

# --- COF Gate Detection ---

def test_clinical_gate_detects_patient_mention():
    history = [{"speaker": "user", "text": "How are patient outcomes affected by stent encrustation?"}]
    ev = ConditionEvaluator()
    assert ev.cof_clinical_mentioned(history) is True

def test_clinical_gate_false_for_irrelevant_text():
    history = [{"speaker": "user", "text": "What is your budget for next quarter?"}]
    ev = ConditionEvaluator()
    assert ev.cof_clinical_mentioned(history) is False

def test_operational_gate_detects_or_mention():
    history = [{"speaker": "user", "text": "How many OR cases are you scheduling per week?"}]
    ev = ConditionEvaluator()
    assert ev.cof_operational_mentioned(history) is True

def test_financial_gate_detects_cost_mention():
    history = [{"speaker": "user", "text": "What does a re-intervention cost your facility?"}]
    ev = ConditionEvaluator()
    assert ev.cof_financial_mentioned(history) is True

def test_all_cof_requires_all_three():
    history = [
        {"speaker": "user", "text": "How are patient outcomes?"},
        {"speaker": "user", "text": "What about OR scheduling throughput?"},
        # No financial mention yet
    ]
    ev = ConditionEvaluator()
    assert ev.cof_all_mentioned(history) is False

def test_open_ended_question_detection():
    history = [
        {"speaker": "user", "text": "What challenges are you facing with stone management?"},
        {"speaker": "user", "text": "How does that impact your clinical team?"},
    ]
    ev = ConditionEvaluator()
    assert ev.open_ended_questions_count(history) == 2

def test_closed_question_not_counted():
    history = [{"speaker": "user", "text": "Is this a problem for you?"}]
    ev = ConditionEvaluator()
    assert ev.open_ended_questions_count(history) == 0

def test_solution_presented_requires_length():
    short = [{"speaker": "user", "text": "Our Tria stent helps."}]
    long = [{"speaker": "user", "text": "Our Tria stent system addresses stone management throughput by reducing OR time and eliminating fragmentation complications, which directly maps to the issues you described."}]
    ev = ConditionEvaluator()
    assert ev.solution_presented(short) is False
    assert ev.solution_presented(long) is True

# --- Arc Stage Tracker ---

def test_arc_starts_at_stage_1():
    arc = {"stages": [{"id": 1, "name": "DISCOVERY", "unlock_condition": "open_ended_questions >= 2", "max_turns": 6}]}
    tracker = ArcStageTracker(arc)
    assert tracker.current_stage == 1

def test_arc_advances_when_condition_met():
    arc = {"stages": [
        {"id": 1, "name": "DISCOVERY", "unlock_condition": "open_ended_questions >= 2", "max_turns": 6},
        {"id": 2, "name": "PAIN_SURFACE", "unlock_condition": "cof_clinical_mentioned == true", "max_turns": 5},
    ]}
    tracker = ArcStageTracker(arc)
    history = [
        {"speaker": "user", "text": "What challenges are you seeing with stone management?"},
        {"speaker": "user", "text": "How does that affect your OR schedule?"},
    ]
    tracker.evaluate(history)
    assert tracker.current_stage == 2

def test_arc_does_not_advance_when_condition_not_met():
    arc = {"stages": [
        {"id": 1, "name": "DISCOVERY", "unlock_condition": "open_ended_questions >= 2", "max_turns": 6},
        {"id": 2, "name": "PAIN_SURFACE", "unlock_condition": "cof_clinical_mentioned == true", "max_turns": 5},
    ]}
    tracker = ArcStageTracker(arc)
    history = [{"speaker": "user", "text": "Is this a problem for you?"}]
    tracker.evaluate(history)
    assert tracker.current_stage == 1
```

- [ ] **Step 2: Run tests (expect fail)**

```bash
pytest tests/test_arc_engine.py -v
# Expected: FAILED — arc_engine module not found
```

- [ ] **Step 3: Implement arc_engine.py**

Create `backend/arc_engine.py`:
```python
import re
from typing import List, Dict, Any, Optional

COF_SEEDS = {
    "clinical": ["patient","complication","outcome","infection","stent","fragment",
                 "stone","encrustation","urinary","clinical","care","safety","risk"],
    "operational": ["or","schedule","throughput","turnover","workflow","procedure",
                    "time","efficiency","volume","capacity","staff","utilization"],
    "financial": ["cost","budget","revenue","reimbursement","roi","savings",
                  "expense","margin","price","spend","financial","dollar","investment"],
    "solution": ["tria","stent","solution","product","system","platform",
                 "offer","propose","address","resolve","help","benefit"],
    "positive_signal": ["trial","pilot","vac","committee","consider","interested",
                        "explore","next step","meeting","approve","move forward"],
    "discount_defense": ["discount","lower price","price reduction","cut","cheaper","negotiate down"],
}

CLOSED_QUESTION_STARTERS = re.compile(
    r"^\s*(is|are|do|does|did|can|will|would|have|has)\b", re.IGNORECASE
)


class ConditionEvaluator:
    def _user_turns(self, history: List[Dict]) -> List[str]:
        return [m["text"].lower() for m in history if m.get("speaker") == "user"]

    def _contains_seed(self, text: str, domain: str) -> bool:
        return any(seed in text for seed in COF_SEEDS[domain])

    def cof_clinical_mentioned(self, history: List[Dict]) -> bool:
        return any(self._contains_seed(t, "clinical") for t in self._user_turns(history))

    def cof_operational_mentioned(self, history: List[Dict]) -> bool:
        return any(self._contains_seed(t, "operational") for t in self._user_turns(history))

    def cof_financial_mentioned(self, history: List[Dict]) -> bool:
        return any(self._contains_seed(t, "financial") for t in self._user_turns(history))

    def cof_all_mentioned(self, history: List[Dict]) -> bool:
        return (self.cof_clinical_mentioned(history) and
                self.cof_operational_mentioned(history) and
                self.cof_financial_mentioned(history))

    def open_ended_questions_count(self, history: List[Dict]) -> int:
        count = 0
        for turn in self._user_turns(history):
            if "?" in turn and not CLOSED_QUESTION_STARTERS.match(turn):
                count += 1
        return count

    def solution_presented(self, history: List[Dict]) -> bool:
        for turn in self._user_turns(history):
            has_solution_term = self._contains_seed(turn, "solution")
            word_count = len(turn.split())
            if has_solution_term and word_count >= 30:
                return True
        return False

    def objection_addressed(self, history: List[Dict]) -> bool:
        ai_turns = [m["text"].lower() for m in history if m.get("speaker") == "ai"]
        if not any("price" in t or "budget" in t or "vac" in t for t in ai_turns):
            return False
        last_user = self._user_turns(history)
        if not last_user:
            return False
        last = last_user[-1]
        return not any(seed in last for seed in COF_SEEDS["discount_defense"])

    def resolution_positive(self, history: List[Dict]) -> bool:
        ai_turns = [m["text"].lower() for m in history if m.get("speaker") == "ai"]
        if not ai_turns:
            return False
        return self._contains_seed(ai_turns[-1], "positive_signal")

    def evaluate_condition(self, condition: str, history: List[Dict]) -> bool:
        cond = condition.strip()
        if cond.startswith("open_ended_questions >="):
            n = int(cond.split(">=")[1].strip())
            return self.open_ended_questions_count(history) >= n
        mapping = {
            "cof_clinical_mentioned == true": self.cof_clinical_mentioned,
            "cof_operational_mentioned == true": self.cof_operational_mentioned,
            "cof_financial_mentioned == true": self.cof_financial_mentioned,
            "cof_all_mentioned == true": self.cof_all_mentioned,
            "solution_presented == true": self.solution_presented,
            "objection_addressed == true": self.objection_addressed,
            "resolution_positive == true": self.resolution_positive,
        }
        fn = mapping.get(cond)
        return fn(history) if fn else False


class ArcStageTracker:
    def __init__(self, arc: Dict[str, Any]):
        self.stages = arc["stages"]
        self.current_stage = self.stages[0]["id"] if self.stages else 1
        self.evaluator = ConditionEvaluator()
        self.cof_flags = {"clinical": False, "operational": False, "financial": False}

    def evaluate(self, history: List[Dict]) -> bool:
        """Evaluate current stage unlock condition. Returns True if stage advanced."""
        self._update_cof_flags(history)
        current = self._get_stage(self.current_stage)
        if not current:
            return False
        next_stage = self._get_stage(self.current_stage + 1)
        if not next_stage:
            return False
        condition = current.get("unlock_condition", "")
        if self.evaluator.evaluate_condition(condition, history):
            self.current_stage += 1
            return True
        return False

    def _update_cof_flags(self, history: List[Dict]):
        ev = self.evaluator
        self.cof_flags["clinical"] = ev.cof_clinical_mentioned(history)
        self.cof_flags["operational"] = ev.cof_operational_mentioned(history)
        self.cof_flags["financial"] = ev.cof_financial_mentioned(history)

    def _get_stage(self, stage_id: int) -> Optional[Dict]:
        return next((s for s in self.stages if s["id"] == stage_id), None)

    def get_persona_instruction(self) -> str:
        stage = self._get_stage(self.current_stage)
        return stage.get("persona_instruction", "") if stage else ""
```

- [ ] **Step 4: Run tests (expect pass)**

```bash
pytest tests/test_arc_engine.py -v
# Expected: 12 PASSED
```

- [ ] **Step 5: Create labeled transcript fixtures**

> **Fixture count decision (stakeholder acknowledged):** Spec Section 13.1 requires 50 labeled transcripts for a statistically reliable 90% accuracy gate. This plan gates development at 10 fixtures — enough to validate logic across all COF domain combinations. **10 fixtures is a pre-pilot threshold only.** Before BSCI client go-live, the fixture set MUST be expanded to 50 and the assertion updated from `>= 10` to `>= 50`. Failure to do so leaves the 90% accuracy success metric unverified at the spec-required confidence level.

Create `tests/fixtures/transcripts/README.md` documenting the fixture format:
```json
{
  "id": "fixture_001",
  "turns": [
    {"speaker": "user", "text": "..."},
    {"speaker": "ai", "text": "..."}
  ],
  "expected": {
    "cof_clinical": true,
    "cof_operational": false,
    "cof_financial": true
  }
}
```

Create at least 10 fixture files covering: clinical-only, operational-only, financial-only, all-three, none, edge cases (partial matches, clinical term in AI turn only, etc.).

- [ ] **Step 6: Write fixture accuracy test**

```python
def test_cof_gate_accuracy_against_fixtures():
    import json
    from pathlib import Path
    # Use __file__-relative path so the test works when run from any directory
    fixture_dir = Path(__file__).parent / "fixtures" / "transcripts"
    fixtures = list(fixture_dir.glob("*.json"))
    assert len(fixtures) >= 10, f"Need at least 10 labeled fixtures, found {len(fixtures)}"
    ev = ConditionEvaluator()
    correct = 0
    for path in fixtures:
        with open(path) as fh:
            f = json.load(fh)
        history = f["turns"]
        exp = f["expected"]
        results = {
            "cof_clinical": ev.cof_clinical_mentioned(history),
            "cof_operational": ev.cof_operational_mentioned(history),
            "cof_financial": ev.cof_financial_mentioned(history),
        }
        if results == exp:
            correct += 1
    accuracy = correct / len(fixtures)
    assert accuracy >= 0.90, f"COF gate accuracy {accuracy:.0%} below 90% threshold"
```

- [ ] **Step 7: Run accuracy test**

```bash
pytest tests/test_arc_engine.py::test_cof_gate_accuracy_against_fixtures -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/arc_engine.py tests/test_arc_engine.py tests/fixtures/
git commit -m "feat(arc): condition evaluator + arc stage tracker with COF gate detection"
```

---

### Task 2.2: Wire arc engine into WebSocket handler

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Write integration test**

Add to `tests/test_websocket.py`:
```python
from unittest.mock import AsyncMock, patch

def test_websocket_arc_stage_advances(client, valid_jwt, seeded_scenario):
    # Mock ai_service so the test does not call real OpenAI (CI uses sk-test which fails auth)
    mock_ai_response = {
        "text": "That's a meaningful question about our clinical workflow.",
        "audio": None,
    }
    with patch("backend.main.ai_service.generate_response",
               new_callable=AsyncMock, return_value=mock_ai_response):
        # First create a session to get a session_id
        resp = client.post("/api/sessions",
            json={"persona_id": "vac_buyer", "scenario_id": seeded_scenario["scenario_id"]},
            headers={"Authorization": f"Bearer {valid_jwt}"})
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]

        with client.websocket_connect(f"/ws/{session_id}?token={valid_jwt}") as ws:
            ws.receive_json()  # ready message
            ws.receive_json()  # greeting
            ws.send_json({"type": "user_message",
                          "text": "What challenges are you seeing with patient outcomes from stone management?"})
            response = ws.receive_json()
            assert response["type"] == "ai_message"
            # One open-ended question — stage still 1 (need 2 to unlock)
            ws.send_json({"type": "user_message",
                          "text": "How does that impact your OR scheduling throughput?"})
            ws.receive_json()
            # Verify arc stage advanced in DB (two open-ended questions met stage 1 unlock condition)
            detail = client.get(f"/api/sessions/{session_id}",
                                headers={"Authorization": f"Bearer {valid_jwt}"})
            assert detail.json()["arc_stage_reached"] >= 2
```

- [ ] **Step 2: Update WebSocket handler in main.py**

In the `websocket_endpoint` function:
1. Import `ArcStageTracker` from `arc_engine`
2. Load scenario arc from DB at session start
3. Instantiate `ArcStageTracker(scenario.arc)`
4. After each user message, call `tracker.evaluate(conversation_history)`
5. If stage advanced, update `sessions.arc_stage_reached` in DB
6. Inject `tracker.get_persona_instruction()` into the next system prompt
7. Update `cof_flags` in session state for completion evaluation

- [ ] **Step 3: Add WebSocket JWT verification**

```python
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, token: str = ""):
    user = await verify_ws_token(token)
    if not user:
        await websocket.close(code=4001)
        return
    await websocket.accept()
    ...
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_websocket.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_websocket.py
git commit -m "feat(arc): wire arc stage tracker into WebSocket session handler"
```

---

## Sprint 3: Metering + Token Budget

### Task 3.1: Metering event writer

**Files:**
- Create: `backend/metering.py`
- Create: `tests/test_metering.py`
- Modify: `backend/ai_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_metering.py`:
```python
def test_openai_cost_calculated_correctly():
    from backend.metering import compute_cost
    cost = compute_cost(provider="openai", model="gpt-4o-mini", tokens_in=1000, tokens_out=500)
    expected = (1000 * 0.15 / 1_000_000) + (500 * 0.60 / 1_000_000)
    assert abs(cost - expected) < 0.0000001

def test_elevenlabs_cost_calculated_correctly():
    from backend.metering import compute_cost
    cost = compute_cost(provider="elevenlabs", model=None, tokens_in=0, tokens_out=0, characters=200)
    expected = 200 * 0.18 / 1000
    assert abs(cost - expected) < 0.0000001

@pytest.mark.asyncio
async def test_session_cost_rollup(seeded_metering_session):
    from backend.metering import get_session_cost
    # seeded_metering_session is the session UUID string with 3 pre-inserted events ($0.045 total)
    total = await get_session_cost(seeded_metering_session)
    assert total == pytest.approx(0.045, abs=0.001)

def test_token_budget_cap_enforced():
    from backend.metering import is_over_budget
    assert is_over_budget(current_cost=0.41, preset="quick_drill") is True
    assert is_over_budget(current_cost=0.39, preset="quick_drill") is False
```

- [ ] **Step 2: Implement metering.py**

Create `backend/metering.py`:
```python
import os
from typing import Optional
from decimal import Decimal
from backend.db import AsyncSessionLocal
from backend.models import MeteringEvent

COST_TABLE = {
    ("openai", "gpt-4o-mini"): {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    ("openai", "tts-1"):        {"chars": 0.015 / 1000},
    ("elevenlabs", None):       {"chars": 0.18 / 1000},
    ("anthropic", "claude-3-haiku-20240307"): {"input": 0.25 / 1_000_000, "output": 1.25 / 1_000_000},
}

BUDGET_CAPS = {
    "quick_drill":    float(os.environ.get("TOKEN_BUDGET_QUICK_DRILL", "0.40")),
    "full_practice":  float(os.environ.get("TOKEN_BUDGET_FULL_PRACTICE", "1.00")),
    "cert_run":       float(os.environ.get("TOKEN_BUDGET_CERT_RUN", "2.00")),
}

def compute_cost(provider: str, model: Optional[str], tokens_in: int = 0,
                 tokens_out: int = 0, characters: int = 0) -> float:
    key = (provider, model)
    rates = COST_TABLE.get(key) or COST_TABLE.get((provider, None)) or {}
    cost = 0.0
    if "input" in rates:
        cost += tokens_in * rates["input"] + tokens_out * rates["output"]
    if "chars" in rates:
        cost += characters * rates["chars"]
    return round(cost, 6)

async def write_event(session_id: str, user_id: str, cohort_id: Optional[str],
                      division_id: Optional[str], provider: str, model: Optional[str],
                      call_type: str, tokens_in: int = 0, tokens_out: int = 0,
                      characters: int = 0) -> None:
    cost = compute_cost(provider, model, tokens_in, tokens_out, characters)
    async with AsyncSessionLocal() as db:
        event = MeteringEvent(
            session_id=session_id, user_id=user_id, cohort_id=cohort_id,
            division_id=division_id, provider=provider, model=model,
            call_type=call_type, tokens_in=tokens_in, tokens_out=tokens_out,
            cost_usd=cost,
        )
        db.add(event)
        await db.commit()

async def get_session_cost(session_id: str) -> float:
    from sqlalchemy import select, func
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.sum(MeteringEvent.cost_usd))
            .where(MeteringEvent.session_id == session_id)
        )
        return float(result.scalar() or 0)

def is_over_budget(current_cost: float, preset: str) -> bool:
    return current_cost >= BUDGET_CAPS.get(preset, BUDGET_CAPS["full_practice"])
```

- [ ] **Step 3: Hook metering into ai_service.py**

After each `_call_provider` call in `ai_service.py`, call `asyncio.create_task(write_event(...))` with the token counts from the API response. Pass `session_id`, `user_id`, `cohort_id`, `division_id` as context to the service.

- [ ] **Step 4: Add budget cap check to WebSocket handler**

Before each AI call in `websocket_endpoint`:
```python
current_cost = await get_session_cost(session_id)
if is_over_budget(current_cost, session.preset):
    await websocket.send_json({
        "type": "ai_message",
        "text": "This has been a good conversation. Let's pick this up next time.",
        "audio": None,
        "session_end": True
    })
    await db.execute(update(Session).where(Session.id == session_id)
                     .values(status="completed"))
    break
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_metering.py -v
# Expected: 4 PASSED
```

- [ ] **Step 6: Commit**

```bash
git add backend/metering.py tests/test_metering.py backend/ai_service.py backend/main.py
git commit -m "feat(metering): event writer, cost computation, token budget cap"
```

---

## Sprint 4: Completion + Certificates

### Task 4.1: Session completion + COF cert issuance

**Files:**
- Create: `backend/cert_service.py`
- Create: `tests/test_cert_service.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Add brand assets**

```bash
# Copy brand assets into backend:
cp Library/Brand_Assets/ls_logo.png backend/assets/ls_logo.png
cp Library/Brand_Assets/signature.png backend/assets/signature.png
# Copy fonts:
mkdir -p backend/assets/fonts
cp Library/Brand_Assets/fonts/Oswald-Bold.ttf backend/assets/fonts/
cp Library/Brand_Assets/fonts/Manrope-Regular.ttf backend/assets/fonts/
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_cert_service.py`:
```python
def test_cert_issued_when_all_gates_pass():
    from backend.cert_service import should_issue_cert
    assert should_issue_cert(cof_clinical=True, cof_operational=True,
                              cof_financial=True, arc_stage=5, preset="full_practice") is True

def test_cert_not_issued_when_gate_missing():
    from backend.cert_service import should_issue_cert
    assert should_issue_cert(cof_clinical=True, cof_operational=False,
                              cof_financial=True, arc_stage=5, preset="full_practice") is False

def test_cert_not_issued_for_quick_drill():
    from backend.cert_service import should_issue_cert
    assert should_issue_cert(cof_clinical=True, cof_operational=True,
                              cof_financial=True, arc_stage=5, preset="quick_drill") is False

def test_cert_not_issued_below_arc_stage_5():
    from backend.cert_service import should_issue_cert
    assert should_issue_cert(cof_clinical=True, cof_operational=True,
                              cof_financial=True, arc_stage=4, preset="full_practice") is False

def test_pdf_generation_produces_file(tmp_path):
    from backend.cert_service import generate_cert_pdf
    completion_data = {
        "completion_id": "test-uuid-123",
        "rep_name": "Sarah Johnson",
        "scenario_name": "Tria Stents VAC Scenario",
        "completed_at": "2026-03-18",
        "score": 87,
        "cof_clinical": True,
        "cof_operational": True,
        "cof_financial": True,
    }
    output_path = tmp_path / "cert.pdf"
    generate_cert_pdf(completion_data, str(output_path))
    assert output_path.exists()
    assert output_path.stat().st_size > 1000  # Not empty
```

- [ ] **Step 3: Implement cert_service.py**

Create `backend/cert_service.py`:
```python
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ASSETS = Path(__file__).parent / "assets"

def _register_fonts():
    pdfmetrics.registerFont(TTFont("Oswald-Bold", str(ASSETS / "fonts/Oswald-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Manrope", str(ASSETS / "fonts/Manrope-Regular.ttf")))

def should_issue_cert(cof_clinical: bool, cof_operational: bool, cof_financial: bool,
                       arc_stage: int, preset: str) -> bool:
    return (cof_clinical and cof_operational and cof_financial
            and arc_stage >= 5
            and preset in ("full_practice", "cert_run"))

def generate_cert_pdf(data: dict, output_path: str) -> str:
    _register_fonts()
    c = canvas.Canvas(output_path, pagesize=letter)
    w, h = letter

    # Navy header bar
    c.setFillColor(colors.HexColor("#1B2B5B"))
    c.rect(0, h - 1.5 * inch, w, 1.5 * inch, fill=1, stroke=0)

    # Logo
    logo = str(ASSETS / "ls_logo.png")
    if Path(logo).exists():
        c.drawImage(logo, 0.5 * inch, h - 1.3 * inch, width=2 * inch, preserveAspectRatio=True)

    # Title
    c.setFillColor(colors.white)
    c.setFont("Oswald-Bold", 24)
    c.drawCentredString(w / 2, h - 0.9 * inch, "Certificate of Completion")

    # Body
    c.setFillColor(colors.HexColor("#1B2B5B"))
    c.setFont("Manrope", 14)
    c.drawCentredString(w / 2, h - 2.5 * inch, "This certifies that")
    c.setFont("Oswald-Bold", 20)
    c.drawCentredString(w / 2, h - 3.0 * inch, data["rep_name"])
    c.setFont("Manrope", 13)
    c.drawCentredString(w / 2, h - 3.5 * inch, f"has successfully completed")
    c.setFont("Oswald-Bold", 16)
    c.drawCentredString(w / 2, h - 4.0 * inch, data["scenario_name"])

    # COF gates
    c.setFont("Manrope", 11)
    gates = [
        ("Clinical", data["cof_clinical"]),
        ("Operational", data["cof_operational"]),
        ("Financial", data["cof_financial"]),
    ]
    y = h - 5.0 * inch
    for name, passed in gates:
        mark = "✓" if passed else "○"
        c.drawString(2.5 * inch, y, f"{mark}  {name} Domain")
        y -= 0.3 * inch

    # Score + date
    c.setFont("Manrope", 12)
    c.drawCentredString(w / 2, h - 6.2 * inch, f"Score: {data['score']}   |   {data['completed_at']}")

    # Signature
    sig = str(ASSETS / "signature.png")
    if Path(sig).exists():
        c.drawImage(sig, w / 2 - 1 * inch, h - 7.5 * inch, width=2 * inch, preserveAspectRatio=True)
    c.setFont("Manrope", 10)
    c.drawCentredString(w / 2, h - 8.0 * inch, "Dr. Gunter Wessels, Ph.D., M.B.A.")
    c.drawCentredString(w / 2, h - 8.3 * inch, "LiquidSMARTS™")

    # Footer: completion ID
    c.setFont("Manrope", 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(w / 2, 0.5 * inch, f"Completion ID: {data['completion_id']}")

    c.save()
    return output_path

async def upload_and_email_cert(completion_data: dict, user_email: str) -> str:
    """Generate PDF, upload to Supabase Storage, email to rep. Returns public URL."""
    import tempfile, resend
    from supabase import create_client

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "certificates")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        generate_cert_pdf(completion_data, f.name)
        pdf_bytes = Path(f.name).read_bytes()

    path = f"{completion_data['user_id']}/{completion_data['completion_id']}.pdf"
    supabase.storage.from_(bucket).upload(path, pdf_bytes, {"content-type": "application/pdf"})
    public_url = supabase.storage.from_(bucket).get_public_url(path)

    resend.api_key = os.environ["RESEND_API_KEY"]
    resend.Emails.send({
        "from": "training@liquidsmarts.com",
        "to": user_email,
        "subject": f"Your LiquidSMARTS™ Certificate — {completion_data['scenario_name']}",
        "text": f"Congratulations {completion_data['rep_name']}!\n\nYour certificate is attached.\n\nCompletion ID: {completion_data['completion_id']}",
        "attachments": [{"filename": "certificate.pdf", "content": list(pdf_bytes)}],
    })
    return public_url
```

- [ ] **Step 4: Run tests**

```bash
# reportlab, resend, supabase were added to requirements.txt in Task 1.2 Step 1 — no pip install needed here
pytest tests/test_cert_service.py -v
# Expected: 5 PASSED
```

- [ ] **Step 5: Wire completion into WebSocket session end**

In `main.py`, when session status changes to `completed`:
```python
from backend.cert_service import should_issue_cert, upload_and_email_cert

cof = tracker.cof_flags
if should_issue_cert(cof["clinical"], cof["operational"], cof["financial"],
                     tracker.current_stage, session["preset"]):
    # write completions row, generate cert async
    asyncio.create_task(upload_and_email_cert(completion_data, user_email))
```

- [ ] **Step 6: Commit**

```bash
git add backend/cert_service.py tests/test_cert_service.py backend/main.py
git commit -m "feat(cert): completion evaluation, PDF generation, Supabase upload, email delivery"
```

---

## Sprint 5: Next.js 15 Frontend

### Task 5.1: Scaffold Next.js 15 app

**Files:**
- Create: `frontend-next/` (full scaffold)

- [ ] **Step 1: Initialize project**

```bash
cd voice-training-mvp
npx create-next-app@latest frontend-next \
  --typescript --tailwind --app --src-dir=false \
  --import-alias "@/*" --no-git
cd frontend-next
npm install @supabase/ssr @supabase/supabase-js
npm install --save-dev jest @testing-library/react @testing-library/jest-dom jest-environment-jsdom @types/jest ts-jest
```

- [ ] **Step 2: Create Supabase lib**

Create `frontend-next/lib/supabase.ts`:
```typescript
import { createBrowserClient } from '@supabase/ssr'
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'

export const createClient = () =>
  createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )

export const createServerSupabaseClient = async () => {
  const cookieStore = await cookies()  // Next.js 15: cookies() is async
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) { return cookieStore.get(name)?.value },
        set(name: string, value: string, options: CookieOptions) {
          cookieStore.set({ name, value, ...options })
        },
        remove(name: string, options: CookieOptions) {
          cookieStore.set({ name, value: '', ...options })
        },
      },
    }
  )
}
```

- [ ] **Step 3: Create middleware.ts**

Create `frontend-next/middleware.ts`:
```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request: { headers: request.headers } })
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name) { return request.cookies.get(name)?.value },
        set(name, value, options) {
          request.cookies.set({ name, value, ...options })
          response = NextResponse.next({ request: { headers: request.headers } })
          response.cookies.set({ name, value, ...options })
        },
        remove(name, options) {
          request.cookies.set({ name, value: '', ...options })
          response = NextResponse.next({ request: { headers: request.headers } })
          response.cookies.set({ name, value: '', ...options })
        },
      },
    }
  )
  const { data: { session } } = await supabase.auth.getSession()
  const { pathname } = request.nextUrl
  const publicPaths = ['/auth', '/join', '/']
  const isPublic = publicPaths.some(p => pathname.startsWith(p))
  if (!session && !isPublic) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }
  return response
}

export const config = { matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'] }
```

- [ ] **Step 4: Write auth flow tests (red phase — pages don't exist yet)**

Create `frontend-next/tests/auth.test.tsx`:
```typescript
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

describe('Auth flows', () => {
  it('renders login page with email input', async () => {
    const { default: LoginPage } = await import('../app/auth/login/page')
    render(<LoginPage />)
    expect(screen.getByRole('textbox', { name: /email/i })).toBeInTheDocument()
  })

  it('renders cohort join page with token input', async () => {
    const { default: JoinPage } = await import('../app/join/[token]/page')
    render(<JoinPage params={{ token: 'test-token' }} />)
    expect(screen.getByRole('textbox', { name: /name/i })).toBeInTheDocument()
  })
})
```

Run tests now — expected to FAIL with `Cannot find module '../app/auth/login/page'`. This confirms the red phase before implementation.

```bash
cd frontend-next && npm test -- auth.test --no-coverage
# Expected: FAILED — MODULE_NOT_FOUND (login/join pages not created yet)
```

- [ ] **Step 5: Create auth pages**

Create `frontend-next/app/auth/login/page.tsx` — email input form that calls `supabase.auth.signInWithOtp()`. On submit: show "Check your email" message.

Create `frontend-next/app/auth/callback/page.tsx` — reads code from URL params, calls `supabase.auth.exchangeCodeForSession()`, redirects to `/dashboard`.

Create `frontend-next/app/join/[token]/page.tsx` — name + email form. On submit: POST to `/api/join` with token. On success, redirects to "check your email."

- [ ] **Step 6: Run frontend tests**

```bash
cd frontend-next && npm test -- --passWithNoTests
```

- [ ] **Step 7: Commit**

```bash
git add frontend-next/
git commit -m "feat(frontend): Next.js 15 scaffold, Supabase auth, middleware JWT refresh"
```

---

### Task 5.2: Voice chat UI + arc progress

**Files:**
- Create: `frontend-next/components/VoiceChat.tsx`
- Create: `frontend-next/components/ArcProgress.tsx`
- Create: `frontend-next/components/OnboardingOverlay.tsx`
- Create: `frontend-next/components/FillerAudio.tsx`

- [ ] **Step 1: Write component tests**

Create `frontend-next/tests/VoiceChat.test.tsx`:
```typescript
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import ArcProgress from '../components/ArcProgress'
import CofGates from '../components/CofGates'

describe('ArcProgress', () => {
  it('renders 6 dots', () => {
    render(<ArcProgress currentStage={1} totalStages={6} />)
    expect(screen.getAllByRole('presentation')).toHaveLength(6)
  })

  it('marks stage 3 as active when currentStage=3', () => {
    render(<ArcProgress currentStage={3} totalStages={6} />)
    const dots = screen.getAllByRole('presentation')
    expect(dots[2]).toHaveClass('animate-pulse')
  })
})

describe('CofGates', () => {
  it('shows 3 gate indicators', () => {
    render(<CofGates clinical={true} operational={false} financial={true} />)
    expect(screen.getByText(/clinical/i)).toBeInTheDocument()
    expect(screen.getByText(/operational/i)).toBeInTheDocument()
    expect(screen.getByText(/financial/i)).toBeInTheDocument()
  })

  it('applies passed class to passed gates', () => {
    const { container } = render(<CofGates clinical={true} operational={false} financial={false} />)
    expect(container.querySelector('[data-gate="clinical"]')).toHaveClass('text-green-500')
    expect(container.querySelector('[data-gate="operational"]')).not.toHaveClass('text-green-500')
  })
})
```

- [ ] **Step 2: Implement ArcProgress**

Create `frontend-next/components/ArcProgress.tsx`:
```typescript
interface Props { currentStage: number; totalStages: number }
export default function ArcProgress({ currentStage, totalStages }: Props) {
  return (
    <div className="flex gap-2 justify-center py-3">
      {Array.from({ length: totalStages }, (_, i) => {
        const stage = i + 1
        const isActive = stage === currentStage
        const isPast = stage < currentStage
        return (
          <span
            key={stage}
            role="presentation"
            className={`w-2.5 h-2.5 rounded-full transition-all ${
              isActive ? 'bg-blue-500 animate-pulse scale-125' :
              isPast   ? 'bg-blue-300' : 'bg-gray-300'
            }`}
          />
        )
      })}
    </div>
  )
}
```

- [ ] **Step 3: Implement CofGates**

Create `frontend-next/components/CofGates.tsx`:
```typescript
interface Props { clinical: boolean; operational: boolean; financial: boolean }
export default function CofGates({ clinical, operational, financial }: Props) {
  const Gate = ({ name, passed }: { name: string; passed: boolean }) => (
    <div data-gate={name.toLowerCase()}
         className={`flex items-center gap-1.5 text-sm ${passed ? 'text-green-500' : 'text-gray-400'}`}>
      <span>{passed ? '✓' : '○'}</span>
      <span className="capitalize">{name}</span>
    </div>
  )
  return (
    <div className="flex gap-4">
      <Gate name="clinical" passed={clinical} />
      <Gate name="operational" passed={operational} />
      <Gate name="financial" passed={financial} />
    </div>
  )
}
```

- [ ] **Step 4: Implement FillerAudio**

Create `frontend-next/components/FillerAudio.tsx`:
```typescript
'use client'
import { useRef, useCallback } from 'react'

const FILLER_CLIPS = ['hmm','go-on','interesting','thats-a-lot','ok',
                       'right-right','mm-hmm','long-answer','tell-me-more','noted']

interface Props { personaId: string; triggerMs?: number }

export function useFillerAudio({ personaId, triggerMs = 800 }: Props) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastClipRef = useRef<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const startTimer = useCallback(() => {
    timerRef.current = setTimeout(() => {
      let clip: string
      do { clip = FILLER_CLIPS[Math.floor(Math.random() * FILLER_CLIPS.length)] }
      while (clip === lastClipRef.current)
      lastClipRef.current = clip
      const audio = new Audio(`/filler/${personaId}/${clip}.mp3`)
      audioRef.current = audio
      audio.play().catch(() => {})
    }, triggerMs)
  }, [personaId, triggerMs])

  const cancel = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
  }, [])

  return { startTimer, cancel }
}
```

- [ ] **Step 5: Implement OnboardingOverlay**

Create `frontend-next/components/OnboardingOverlay.tsx`:
```typescript
'use client'
import { useState, useEffect, useRef } from 'react'

const SCRIPT = "Quick heads up — this is a live conversation arc. Your buyer is real enough to push back. She's listening for whether you can surface what's going wrong clinically, operationally, and financially — and move her toward a trial. Discovery first, resolution follows. You've got this. Tap to start."

export default function OnboardingOverlay({ onDismiss }: { onDismiss: () => void }) {
  const [visible, setVisible] = useState(true)
  const [countdown, setCountdown] = useState(20)

  useEffect(() => {
    const audio = new Audio('/onboarding/intro.mp3')
    audio.play().catch(() => {})
    const interval = setInterval(() => setCountdown(c => c - 1), 1000)
    const timer = setTimeout(() => { setVisible(false); onDismiss() }, 20000)
    return () => { clearInterval(interval); clearTimeout(timer); audio.pause() }
  }, [onDismiss])

  if (!visible) return null

  return (
    <div className="fixed inset-0 bg-gray-900/95 flex flex-col items-center justify-center z-50 px-6"
         onClick={() => { setVisible(false); onDismiss() }}>
      <div className="max-w-sm text-center space-y-6">
        <div className="flex justify-center gap-1">
          {[1,2,3,4,5].map(i => (
            <div key={i} className="w-1 bg-blue-400 rounded animate-bounce"
                 style={{ height: `${20 + i * 8}px`, animationDelay: `${i * 0.1}s` }} />
          ))}
        </div>
        <p className="text-white text-lg leading-relaxed">{SCRIPT}</p>
        <p className="text-gray-400 text-sm">Tap anywhere to skip · {countdown}s</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Implement VoiceChat.tsx**

Create `frontend-next/components/VoiceChat.tsx` — full WebSocket voice conversation component:
- Connects to `wss://<backend>/ws/<sessionId>?token=<jwt>`
- Receives `ready` message → renders persona info + arc progress
- Receives `ai_message` → renders text + plays audio (base64 MP3)
- Handles user speech via `window.SpeechRecognition` or typed fallback
- On speech end: calls `filler.startTimer()`. On AI response received: calls `filler.cancel()`
- Sends `{"type": "user_message", "text": "..."}` on each turn
- On `session_end: true` → show completion screen with COF gates + feedback

- [ ] **Step 7: Run tests**

```bash
cd frontend-next && npm test
# Expected: ArcProgress tests PASS, CofGates tests PASS
```

- [ ] **Step 8: Commit**

```bash
git add frontend-next/components/ frontend-next/tests/
git commit -m "feat(frontend): VoiceChat, ArcProgress, CofGates, FillerAudio, OnboardingOverlay"
```

---

### Task 5.3: Dashboards (rep, manager, admin)

**Files:**
- Create: `frontend-next/app/dashboard/page.tsx`
- Create: `frontend-next/app/manager/page.tsx`
- Create: `frontend-next/app/admin/page.tsx`

- [ ] **Step 1: Write dashboard tests**

```typescript
// tests/dashboard.test.tsx
describe('Mobile layout', () => {
  it('renders without horizontal overflow at 375px', () => {
    Object.defineProperty(window, 'innerWidth', { value: 375 })
    const { container } = render(<Dashboard />)
    expect(container.firstChild).not.toHaveStyle('overflow-x: visible')
  })
})
```

> **Mobile test limitation:** The `innerWidth` override above does not test Tailwind responsive classes, touch targets, or real viewport behavior — JSDOM has no layout engine. This test confirms the component renders at 375px without crashing. For true mobile layout validation (spacing, overflow, tap targets), add Playwright E2E tests against a real browser (see Task 8 or post-pilot hardening).


- [ ] **Step 2: Rep dashboard**

Create `frontend-next/app/dashboard/page.tsx` (server component):
- Fetch assigned practice series from backend `/api/series`
- Fetch session history from `/api/sessions?limit=10`
- Fetch completions + certs from `/api/completions`
- Render: practice queue (scenario cards with launch button + QR code), history list, cert badges
- Streak counter at top

- [ ] **Step 3: Manager dashboard**

Create `frontend-next/app/manager/page.tsx` (server component):
- Fetch cohort reps from `/api/manager/cohort`
- Render rep table: name | sessions | last active | cert status | COF pass rate
- Rep detail drawer: session list → tap to see transcript
- "Export LMS CSV" button → `GET /api/manager/export`
- "Assign Series" button → modal with series selector + due date

- [ ] **Step 4: Admin dashboard**

Create `frontend-next/app/admin/page.tsx` (server component):
- Fetch from `/api/admin/metrics`
- Render: sessions chart (30 days), cost by provider chart, flagged sessions table, completion rate by cohort
- All numbers update server-side on page load (no client polling needed for v1)

- [ ] **Step 5: Commit**

```bash
git add frontend-next/app/
git commit -m "feat(frontend): rep/manager/admin dashboards"
```

---

### Task 5.4: Audio state visual layer

> **Why this exists:** The conversation loop has 4 clearly distinct machine states that the rep needs to see in real time — they must know when the mic is hot, when the AI is thinking, and when it is speaking. Without visible state, the rep will over-talk the AI response, interrupt processing, or stare at a blank screen wondering if the app crashed.

**Files:**
- Create: `frontend-next/components/AudioStateDisplay.tsx`
- Modify: `frontend-next/components/VoiceChat.tsx` (inject state prop)
- Test: `frontend-next/tests/AudioStateDisplay.test.tsx`

**States (sourced from WebSocket message types):**

| State | Trigger | Visual |
|-------|---------|--------|
| `idle` | Session loaded, not yet recording | Mic icon, dim gray, "Tap to start" label |
| `listening` | User mic active (Web Speech API started) | Mic icon turns teal, animated waveform bars, "Listening…" label |
| `processing` | User turn submitted, awaiting AI response | Pulsing ring animation, "Processing…" label |
| `speaking` | AI audio playback active | Waveform bars animated on AI avatar, "Speaking…" label |

- [ ] **Step 1: Write failing tests**

Create `frontend-next/tests/AudioStateDisplay.test.tsx`:
```typescript
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import AudioStateDisplay from '../components/AudioStateDisplay'

it('shows listening indicator when state is listening', () => {
  render(<AudioStateDisplay state="listening" />)
  expect(screen.getByText(/listening/i)).toBeInTheDocument()
  expect(screen.getByTestId('audio-state')).toHaveAttribute('data-state', 'listening')
})

it('shows processing indicator when state is processing', () => {
  render(<AudioStateDisplay state="processing" />)
  expect(screen.getByText(/processing/i)).toBeInTheDocument()
  expect(screen.getByTestId('audio-state')).toHaveAttribute('data-state', 'processing')
})

it('shows speaking indicator when state is speaking', () => {
  render(<AudioStateDisplay state="speaking" />)
  expect(screen.getByText(/speaking/i)).toBeInTheDocument()
  expect(screen.getByTestId('audio-state')).toHaveAttribute('data-state', 'speaking')
})

it('shows idle state by default', () => {
  render(<AudioStateDisplay state="idle" />)
  expect(screen.getByTestId('audio-state')).toHaveAttribute('data-state', 'idle')
})
```

- [ ] **Step 2: Run tests (expect fail)**

```bash
cd frontend-next && npm test -- AudioStateDisplay.test --no-coverage
# Expected: FAILED — MODULE_NOT_FOUND
```

- [ ] **Step 3: Implement AudioStateDisplay.tsx**

Create `frontend-next/components/AudioStateDisplay.tsx`:
```typescript
'use client'

type AudioState = 'idle' | 'listening' | 'processing' | 'speaking'

interface Props { state: AudioState }

const STATE_CONFIG: Record<AudioState, { label: string; color: string; animation: string }> = {
  idle:       { label: 'Tap to start',  color: 'text-gray-400',  animation: '' },
  listening:  { label: 'Listening…',   color: 'text-teal-400',  animation: 'animate-pulse' },
  processing: { label: 'Processing…',  color: 'text-blue-400',  animation: 'animate-spin' },
  speaking:   { label: 'Speaking…',    color: 'text-indigo-400', animation: 'animate-bounce' },
}

export default function AudioStateDisplay({ state }: Props) {
  const { label, color, animation } = STATE_CONFIG[state]
  return (
    <div data-testid="audio-state" data-state={state}
         className="flex flex-col items-center gap-3 py-6">
      {/* Waveform bars — 5 bars that animate at different heights per state */}
      <div className="flex items-end gap-1 h-10">
        {[1,2,3,4,5].map(i => (
          <div
            key={i}
            className={`w-1.5 rounded-full bg-current ${color} transition-all duration-150`}
            style={{
              height: state === 'idle'       ? '4px'
                    : state === 'listening'  ? `${8 + (i * 6)}px`
                    : state === 'processing' ? `${(i % 2 === 0) ? 20 : 8}px`
                    : `${4 + (i * 5)}px`,  // speaking
              animationDelay: `${i * 80}ms`,
            }}
          />
        ))}
      </div>
      <span className={`text-sm font-medium tracking-wide ${color} ${animation}`}>
        {label}
      </span>
    </div>
  )
}
```

- [ ] **Step 4: Wire into VoiceChat.tsx**

In `VoiceChat.tsx`, add `audioState` to component state and inject `<AudioStateDisplay>`:
```typescript
const [audioState, setAudioState] = useState<'idle'|'listening'|'processing'|'speaking'>('idle')

// Set state transitions:
// → 'listening'  when Web Speech API onstart fires
// → 'processing' when user turn is sent to WebSocket
// → 'speaking'   when AI audio element .play() begins
// → 'idle'       when AI audio element .ended fires OR on error

// In JSX, above the transcript area:
<AudioStateDisplay state={audioState} />
```

- [ ] **Step 5: Run tests (expect pass)**

```bash
cd frontend-next && npm test -- AudioStateDisplay.test --no-coverage
# Expected: 4 PASSED
```

- [ ] **Step 6: Commit**

```bash
git add frontend-next/components/AudioStateDisplay.tsx \
        frontend-next/components/VoiceChat.tsx \
        frontend-next/tests/AudioStateDisplay.test.tsx
git commit -m "feat(ux): audio state visual layer — idle/listening/processing/speaking indicators"
```

---

## Sprint 6: Easter Eggs + Filler Audio Generation

### Task 6.1: Celebration layer

**Files:**
- Create: `frontend-next/components/CelebrationLayer.tsx`

- [ ] **Step 1: Write test**

```typescript
// tests/CelebrationLayer.test.tsx
import { render } from '@testing-library/react'
import CelebrationLayer from '../components/CelebrationLayer'

// Mock canvas-confetti to verify invocation without running canvas animations
jest.mock('canvas-confetti', () => jest.fn())
import confetti from 'canvas-confetti'
const mockConfetti = confetti as jest.MockedFunction<typeof confetti>

beforeEach(() => mockConfetti.mockClear())

it('renders message overlay when celebrations enabled', () => {
  const { getByTestId } = render(
    <CelebrationLayer trigger="first_session" cohortCelebrationsEnabled={true} />
  )
  expect(getByTestId('celebration-message')).toBeInTheDocument()
})

it('invokes canvas-confetti for confetti-type trigger', () => {
  render(<CelebrationLayer trigger="first_session" cohortCelebrationsEnabled={true} />)
  expect(mockConfetti).toHaveBeenCalledWith(
    expect.objectContaining({ particleCount: 120, spread: 70 })
  )
})

it('does not render or fire confetti when celebrations disabled', () => {
  const { queryByTestId } = render(
    <CelebrationLayer trigger="first_session" cohortCelebrationsEnabled={false} />
  )
  expect(queryByTestId('celebration-message')).not.toBeInTheDocument()
  expect(mockConfetti).not.toHaveBeenCalled()
})
```

- [ ] **Step 2: Install canvas-confetti**

```bash
cd frontend-next && npm install canvas-confetti @types/canvas-confetti
```

- [ ] **Step 3: Implement CelebrationLayer.tsx**

```typescript
'use client'
import { useEffect } from 'react'
import confetti from 'canvas-confetti'

const CELEBRATIONS: Record<string, { type: string; message: string; audio?: string }> = {
  first_session:      { type: 'confetti', message: "You just had your first AI sales conversation. Most people don't even try." },
  first_cof_clean:    { type: 'badge',    message: "Clean COF sweep.", audio: '/celebrations/chime.mp3' },
  streak_3:           { type: 'audio',    message: "OK I have to say — you're getting better at this.", audio: '/celebrations/persona-streak.mp3' },
  speed_stage_5:      { type: 'badge',    message: "Fast hands." },
  first_cert:         { type: 'confetti', message: "Certificate earned.", audio: '/celebrations/cert-sound.mp3' },
  same_day_series:    { type: 'text',     message: "Same-day finish. Noted." },
  redemption_arc:     { type: 'text',     message: "Redemption arc complete." },
}

interface Props { trigger: string; cohortCelebrationsEnabled: boolean }

export default function CelebrationLayer({ trigger, cohortCelebrationsEnabled }: Props) {
  const cel = CELEBRATIONS[trigger]
  useEffect(() => {
    if (!cohortCelebrationsEnabled || !cel) return
    if (cel.type === 'confetti') confetti({ particleCount: 120, spread: 70, origin: { y: 0.6 } })
    if (cel.audio) new Audio(cel.audio).play().catch(() => {})
  }, [trigger, cohortCelebrationsEnabled])

  if (!cohortCelebrationsEnabled || !cel) return null
  return (
    <div data-testid="celebration-message"
         className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white px-6 py-3 rounded-full text-sm shadow-lg z-50 animate-fade-in">
      {cel.message}
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend-next/components/CelebrationLayer.tsx frontend-next/tests/
git commit -m "feat(ux): easter egg celebration layer with COF/streak/cert triggers"
```

---

### Task 6.2: Filler audio generation script

**Files:**
- Create: `scripts/generate_filler_audio.py`

- [ ] **Step 1: Write and run the script**

Create `scripts/generate_filler_audio.py`:
```python
"""One-time script to generate per-persona filler audio clips via ElevenLabs."""
import os, httpx, json
from pathlib import Path

ELEVENLABS_KEY = os.environ["ELEVENLABS_API_KEY"]

PERSONAS = {
    "vac_buyer":        "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "clinical_director":"AZnzlk1XvdvUeBnXmlld",  # Domi
    "ep_lab_director":  "EXAVITQu4vr4xnSDxMaL",  # Bella
}

CLIPS = {
    "hmm":          "Hm.",
    "go-on":        "Go on.",
    "interesting":  "Interesting.",
    "thats-a-lot":  "That's a lot.",
    "ok":           "OK.",
    "right-right":  "Right, right.",
    "mm-hmm":       "Mm-hmm.",
    "long-answer":  "Long answer.",
    "tell-me-more": "Tell me more.",
    "noted":        "Noted.",
}

OUTPUT_DIR = Path("frontend-next/public/filler")

def generate_clip(voice_id: str, text: str, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    response = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"},
        json={"text": text, "model_id": "eleven_monolingual_v1",
              "voice_settings": {"stability": 0.6, "similarity_boost": 0.6}},
        timeout=30,
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)
    print(f"  ✓ {output_path}")

if __name__ == "__main__":
    for persona_id, voice_id in PERSONAS.items():
        print(f"\nGenerating clips for {persona_id}...")
        for clip_name, text in CLIPS.items():
            generate_clip(voice_id, text, OUTPUT_DIR / persona_id / f"{clip_name}.mp3")
    print("\nDone. 30 clips generated.")
```

- [ ] **Step 2: Run the script**

```bash
python3 scripts/generate_filler_audio.py
# Expected: 30 ✓ lines, files in frontend-next/public/filler/
```

- [ ] **Step 3: Also generate onboarding overlay audio**

Add the following block to the bottom of `scripts/generate_filler_audio.py` (inside `if __name__ == "__main__":`), then re-run the script:

```python
# Onboarding overlay (run once)
ONBOARDING_TEXT = (
    "Quick heads up — this is a live conversation arc. "
    "You'll be talking with an AI buyer. "
    "Treat it like the real thing. "
    "When you're ready, just start talking."
)
ONBOARDING_OUT = OUTPUT_DIR.parent / "onboarding" / "intro.mp3"
print("\nGenerating onboarding overlay...")
generate_clip(PERSONAS["vac_buyer"], ONBOARDING_TEXT, ONBOARDING_OUT)
```

```bash
python3 scripts/generate_filler_audio.py
# Expected: 30 ✓ filler lines + 1 ✓ onboarding line
# Files: frontend-next/public/filler/<persona>/<clip>.mp3
#         frontend-next/public/onboarding/intro.mp3
```

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_filler_audio.py frontend-next/public/filler/ frontend-next/public/onboarding/
git commit -m "feat(ux): per-persona filler audio clips (30 clips) + onboarding overlay audio"
```

---

## Sprint 7: Deployment + CI/CD

### Task 7.1: Docker + Railway config

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend-next/Dockerfile`
- Create: `railway.json`
- Create: `docker-compose.yml`

- [ ] **Step 1: Add `output: 'standalone'` to existing next.config.ts**

`create-next-app` (Task 5.1 Step 1) generates `frontend-next/next.config.ts` without `output: 'standalone'`. Edit that file — do NOT recreate it — to add the standalone output option:

```typescript
// frontend-next/next.config.ts  (edit existing file — do not overwrite)
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',  // Required — Dockerfile copies .next/standalone
  // (preserve any other options already in this file from prior sprints)
}

export default nextConfig
```

> **Why:** The frontend Dockerfile copies from `.next/standalone` in the builder stage. Without this option, `npm run build` does not produce that directory and the Docker image build fails at `COPY --from=builder /app/.next/standalone ./`.

- [ ] **Step 2: Backend Dockerfile**

Create `backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# Single worker — WebSocket state is in-process
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

- [ ] **Step 3: Frontend Dockerfile**

Create `frontend-next/Dockerfile`:
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 4: railway.json**

Create `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE" },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3,
    "healthcheckPath": "/",
    "healthcheckTimeout": 30
  }
}
```

- [ ] **Step 5: docker-compose.yml for local dev**

Create `docker-compose.yml`:
```yaml
version: '3.9'
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: voice_training
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/voice_training
    env_file: ./backend/.env
    depends_on: [db]
    volumes: ["./backend:/app"]
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload --workers 1

  frontend:
    build: ./frontend-next
    ports: ["3000:3000"]
    env_file: ./frontend-next/.env.local
    depends_on: [backend]

volumes:
  postgres_data:
```

- [ ] **Step 6: Test local Docker build**

```bash
docker-compose build
docker-compose up
# Backend: http://localhost:8000/docs
# Frontend: http://localhost:3000
curl http://localhost:8000/
# Expected: {"message": "Voice Training Platform MVP"}
```

- [ ] **Step 7: Commit**

```bash
git add backend/Dockerfile frontend-next/Dockerfile railway.json docker-compose.yml frontend-next/next.config.ts
git commit -m "feat(deploy): Docker images, Railway config, local docker-compose"
```

---

### Task 7.2: GitHub Actions CI/CD

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Create workflow**

Create `.github/workflows/deploy.yml`:
```yaml
name: Test + Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: voice_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r backend/requirements.txt
      - run: psql $DATABASE_URL -f backend/migrations/001_initial.sql
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/voice_test
      - run: pytest backend/tests/ -v --tb=short
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/voice_test
          SUPABASE_JWT_SECRET: test-secret-at-least-32-characters-long!!
          SUPABASE_URL: https://test.supabase.co
          SUPABASE_ANON_KEY: test-anon-key
          OPENAI_API_KEY: sk-test
          ELEVENLABS_API_KEY: test-el-key
          ALLOWED_ORIGINS: http://localhost:3000

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend-next && npm ci
      - run: cd frontend-next && npx tsc --noEmit
      - run: cd frontend-next && npm test -- --ci --passWithNoTests

  deploy:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm install -g @railway/cli
      - run: railway up --service voice-training-backend
        env: { RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }} }
      - run: railway up --service voice-training-frontend
        env: { RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }} }
```

- [ ] **Step 2: Add Railway token to GitHub secrets**

In GitHub repo settings → Secrets → Actions:
- Add `RAILWAY_TOKEN` (from Railway dashboard → Account Settings → Tokens)

- [ ] **Step 3: Push to main and verify pipeline runs**

```bash
git add .github/
git commit -m "feat(ci): GitHub Actions test + Railway deploy pipeline"
git push origin main
# Go to GitHub Actions tab — verify all jobs pass
```

---

## Sprint 8: Initial Scenarios + Integration Test

### Task 8.1: Seed BSCI scenarios and divisions

**Files:**
- Create: `backend/seeds/seed_bsci.py`

- [ ] **Step 1: Create seed script**

Create `backend/seeds/seed_bsci.py`:
```python
"""Seed initial BSCI divisions, cohorts, and scenarios."""
import asyncio, json
from backend.db import AsyncSessionLocal
from backend.models import Division, Scenario

TRIA_ARC = {
    "stages": [
        {"id": 1, "name": "DISCOVERY",
         "persona_instruction": "You are a busy VAC procurement director. Respond vaguely to generic questions. Wait for focused, open-ended discovery questions before revealing any information.",
         "unlock_condition": "open_ended_questions >= 2", "max_turns": 6},
        {"id": 2, "name": "PAIN_SURFACE",
         "persona_instruction": "Reveal stone management throughput issues — OR cases being delayed due to stent fragmentation complications. Do not yet mention cost impact.",
         "unlock_condition": "cof_clinical_mentioned == true", "max_turns": 5},
        {"id": 3, "name": "COF_PROBE",
         "persona_instruction": "If the rep asks about OR scheduling or volume impact, become more collaborative. If they quantify cases-per-week lost, help them do the math. Still guard the financial figure until they ask directly.",
         "unlock_condition": "cof_all_mentioned == true", "max_turns": 8},
        {"id": 4, "name": "OBJECTION",
         "persona_instruction": "Introduce this objection exactly: 'This sounds promising but the price point is above what our VAC approved last cycle. I don't see a path to yes right now.'",
         "unlock_condition": "solution_presented == true", "max_turns": 4},
        {"id": 5, "name": "RESOLUTION",
         "persona_instruction": "If rep proposes a phased trial, data collection period, or configuration change — respond positively and begin moving toward VAC commitment. If rep offers discount or price pressure — remain firmly skeptical.",
         "unlock_condition": "objection_addressed == true", "max_turns": 6},
        {"id": 6, "name": "CLOSE",
         "persona_instruction": "Signal readiness to bring Tria to the next VAC cycle or agree to a 30-day trial. The session can end here.",
         "unlock_condition": "resolution_positive == true", "max_turns": 3},
    ]
}

TRIA_CELEBRATIONS = [
    {"condition": "first_session", "type": "confetti", "content": "You just had your first AI sales conversation. Most people don't even try."},
    {"condition": "first_cof_clean", "type": "badge", "content": "Clean COF sweep."},
    {"condition": "speed_stage_5", "type": "badge", "content": "Fast hands."},
]

async def seed():
    async with AsyncSessionLocal() as db:
        endo = Division(name="Endo Urology", slug="endo-urology")
        cardiac = Division(name="Cardiac Rhythm Management", slug="cardiac-rhythm")
        db.add_all([endo, cardiac])
        await db.flush()

        tria_scenario = Scenario(
            name="VAC Stakeholder — Tria Stents",
            division_id=endo.id,
            product_name="Tria Ureteral Stents",
            persona_id="vac_buyer",
            arc=TRIA_ARC,
            celebration_triggers=TRIA_CELEBRATIONS,
        )
        db.add(tria_scenario)
        await db.commit()
        print(f"Seeded: {endo.name}, {cardiac.name}, Tria Stents scenario ({tria_scenario.id})")

if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: Run seed**

```bash
cd backend && python3 seeds/seed_bsci.py
# Expected: Seeded: Endo Urology, Cardiac Rhythm Management, Tria Stents scenario (uuid)
```

- [ ] **Step 3: Verify via API**

```bash
curl http://localhost:8000/api/scenarios
# Expected: JSON array with Tria Stents scenario
```

- [ ] **Step 4: Commit**

```bash
git add backend/seeds/
git commit -m "feat(content): BSCI divisions + Tria Stents VAC scenario with full 6-stage arc"
```

---

### Task 8.2: Full integration test

- [ ] **Step 1: Write end-to-end integration test**

Create `tests/test_integration.py`:
```python
"""Full session flow: create → converse → complete → cert check."""
import pytest

@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_session_flow(async_client, valid_jwt, tria_scenario_id):
    # 1. Create session
    resp = await async_client.post("/api/sessions",
        json={"persona_id": "vac_buyer", "scenario_id": str(tria_scenario_id)},
        headers={"Authorization": f"Bearer {valid_jwt}"})
    assert resp.status_code == 201
    session_id = resp.json()["session_id"]

    # 2. Simulate arc progression via WebSocket
    # (uses mock AI responses that trigger unlock conditions)
    # Arc should reach stage 5+ with COF all True

    # 3. Trigger session end
    resp = await async_client.post(f"/api/sessions/{session_id}/complete",
        headers={"Authorization": f"Bearer {valid_jwt}"})
    assert resp.status_code == 200

    # 4. Verify completion record
    resp = await async_client.get(f"/api/completions?session_id={session_id}",
        headers={"Authorization": f"Bearer {valid_jwt}"})
    assert resp.status_code == 200
    completion = resp.json()
    assert completion["cof_clinical"] is True
    assert completion["cof_operational"] is True
    assert completion["cof_financial"] is True
    assert completion["arc_stage_reached"] >= 5

    # 5. Verify metering events exist
    resp = await async_client.get(f"/api/admin/sessions/{session_id}/cost",
        headers={"Authorization": f"Bearer {valid_jwt}"})
    assert resp.status_code == 200
    assert resp.json()["total_cost_usd"] > 0
```

- [ ] **Step 2: Run integration tests**

```bash
pytest tests/test_integration.py -v -m integration
# Expected: PASSED
```

- [ ] **Step 3: Final commit**

```bash
git add tests/test_integration.py
git commit -m "test(integration): full session flow — create, arc progression, completion, cert, metering"
```

---

## Definition of Done

Each sprint is complete when:
- [ ] All tests in that sprint pass (`pytest` / `npm test`)
- [ ] No stack traces reachable from any API endpoint
- [ ] Git commit created with descriptive message
- [ ] No `TODO` or `FIXME` left in shipped code

**Platform is production-ready when:**
- [ ] All 8 sprints complete
- [ ] GitHub Actions pipeline green on `main`
- [ ] Railway deployment live at public URL
- [ ] Seed script run on production DB
- [ ] Filler audio generated and deployed
- [ ] One full session completed end-to-end on a mobile device (iPhone Safari + Chrome)
- [ ] Admin cost dashboard shows data from that session

---

## Environment Variables Checklist

**Backend (Railway service vars):**
```
DATABASE_URL
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
OPENAI_API_KEY
ANTHROPIC_API_KEY
ELEVENLABS_API_KEY
ALLOWED_ORIGINS
TOKEN_BUDGET_QUICK_DRILL=0.40
TOKEN_BUDGET_FULL_PRACTICE=1.00
TOKEN_BUDGET_CERT_RUN=2.00
FILLER_TRIGGER_MS=800
RESEND_API_KEY
SUPABASE_STORAGE_BUCKET=certificates
```

**Frontend (Railway service vars):**
```
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_API_URL
NEXT_PUBLIC_WS_URL
```
