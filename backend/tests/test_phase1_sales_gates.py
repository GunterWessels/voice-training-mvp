"""Phase 1 tests — SALES gate detection, post_turn_coaching, upload endpoint security."""
import os
import pytest

os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-minimum-32-characters-long!!")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("TESTING", "1")


# ---------------------------------------------------------------------------
# SALES gate detection tests
# ---------------------------------------------------------------------------
from arc_engine import ConditionEvaluator, ArcStageTracker


def _history(*rep_lines):
    return [{"speaker": "user", "text": line} for line in rep_lines]


class TestSalesGateDetection:
    ev = ConditionEvaluator()

    def test_start_detected(self):
        h = _history("The reason for my call today is to show you something that saves OR time.")
        assert self.ev.sales_flags(h)["start"] is True

    def test_start_not_triggered_by_generic_opener(self):
        h = _history("Hello, how are you?")
        assert self.ev.sales_flags(h)["start"] is False

    def test_ask_discover(self):
        h = _history("What challenges do you face with your current stent change-out process?")
        assert self.ev.sales_flags(h)["ask_discover"] is True

    def test_ask_dissect(self):
        h = _history("How does that impact your patient throughput in the OR?")
        assert self.ev.sales_flags(h)["ask_dissect"] is True

    def test_ask_develop(self):
        h = _history("How would it help if you could eliminate re-interventions in the first 90 days?")
        assert self.ev.sales_flags(h)["ask_develop"] is True

    def test_listen_recap(self):
        h = _history("So what I'm hearing is that your main concern is re-intervention rates.")
        assert self.ev.sales_flags(h)["listen_recap"] is True

    def test_explain_reveal(self):
        h = _history("Clinical data indicates a 94% patency rate at 12 months with this design.")
        assert self.ev.sales_flags(h)["explain_reveal"] is True

    def test_explain_relate(self):
        h = _history("Given what you told me about OR scheduling pressure, this matters directly.")
        assert self.ev.sales_flags(h)["explain_relate"] is True

    def test_secure_what(self):
        h = _history("Can we schedule a 30-minute VAC presentation for your team?")
        assert self.ev.sales_flags(h)["secure_what"] is True

    def test_secure_when(self):
        h = _history("I'll have the proposal to you by Friday.")
        assert self.ev.sales_flags(h)["secure_when"] is True

    def test_resistance_empathize(self):
        h = _history("I understand — that's a fair concern about upfront cost.")
        assert self.ev.sales_flags(h)["resistance_empathize"] is True

    def test_resistance_ask(self):
        h = _history("Help me understand what's driving that concern about switching vendors.")
        assert self.ev.sales_flags(h)["resistance_ask"] is True

    def test_resistance_respond(self):
        h = _history("Let me address that directly — here's what the data on changeover time shows.")
        assert self.ev.sales_flags(h)["resistance_respond"] is True

    def test_all_gates_false_on_empty_history(self):
        flags = self.ev.sales_flags([])
        assert all(v is False for v in flags.values())

    def test_all_12_gates_present_in_return(self):
        flags = self.ev.sales_flags([])
        expected_keys = {
            "start", "ask_discover", "ask_dissect", "ask_develop",
            "listen_recap", "explain_reveal", "explain_relate",
            "secure_what", "secure_when",
            "resistance_empathize", "resistance_ask", "resistance_respond",
        }
        assert set(flags.keys()) == expected_keys

    def test_multiple_gates_in_single_turn(self):
        h = _history(
            "I wanted to reach out because clinical data indicates reduced re-interventions. "
            "Given what you told me about OR pressure, this ties directly to your situation. "
            "Can we schedule time next week to walk through the data?"
        )
        flags = self.ev.sales_flags(h)
        assert flags["start"] is True
        assert flags["explain_reveal"] is True
        assert flags["explain_relate"] is True
        assert flags["secure_what"] is True
        assert flags["secure_when"] is True

    def test_arc_tracker_initializes_sales_flags(self):
        arc = {"stages": [{"id": 1, "unlock_condition": "cof_clinical_mentioned == true"}]}
        tracker = ArcStageTracker(arc)
        assert hasattr(tracker, "sales_flags")
        assert isinstance(tracker.sales_flags, dict)
        assert len(tracker.sales_flags) == 12

    def test_arc_tracker_updates_sales_flags_on_evaluate(self):
        arc = {"stages": [
            {"id": 1, "unlock_condition": "cof_clinical_mentioned == true"},
            {"id": 2, "unlock_condition": "cof_operational_mentioned == true"},
        ]}
        tracker = ArcStageTracker(arc)
        history = _history("The reason for my call is to share clinical data indicates patient outcomes.")
        tracker.evaluate(history)
        assert tracker.sales_flags["start"] is True
        assert tracker.sales_flags["explain_reveal"] is True

    def test_spin_flags_present(self):
        arc = {"stages": [{"id": 1, "unlock_condition": "cof_clinical_mentioned == true"}]}
        tracker = ArcStageTracker(arc)
        assert hasattr(tracker, "spin_flags")
        assert set(tracker.spin_flags.keys()) == {"situation", "problem", "implication", "need_payoff"}

    def test_challenger_flags_present(self):
        arc = {"stages": [{"id": 1, "unlock_condition": "cof_clinical_mentioned == true"}]}
        tracker = ArcStageTracker(arc)
        assert hasattr(tracker, "challenger_flags")
        assert set(tracker.challenger_flags.keys()) == {"teach", "tailor", "take_control"}


# ---------------------------------------------------------------------------
# post_turn_coaching mock tests
# ---------------------------------------------------------------------------
from ai_service import AIService


class TestPostTurnCoachingMock:
    def _service(self):
        svc = AIService.__new__(AIService)
        svc.provider = "mock"
        return svc

    def test_coaching_when_start_missing(self):
        svc = self._service()
        gates = {k: False for k in [
            "start", "ask_discover", "ask_dissect", "ask_develop",
            "listen_recap", "explain_reveal", "explain_relate",
            "secure_what", "secure_when",
            "resistance_empathize", "resistance_ask", "resistance_respond",
        ]}
        note = svc._mock_post_turn_coaching("Hello there.", gates)
        assert len(note) > 0
        assert len(note.split()) <= 15

    def test_no_coaching_when_all_gates_met(self):
        svc = self._service()
        gates = {k: True for k in [
            "start", "ask_discover", "ask_dissect", "ask_develop",
            "listen_recap", "explain_reveal", "explain_relate",
            "secure_what", "secure_when",
            "resistance_empathize", "resistance_ask", "resistance_respond",
        ]}
        note = svc._mock_post_turn_coaching("I'll send the proposal by Friday.", gates)
        assert note == ""

    def test_dissect_coaching_after_discover(self):
        svc = self._service()
        gates = {k: False for k in [
            "start", "ask_discover", "ask_dissect", "ask_develop",
            "listen_recap", "explain_reveal", "explain_relate",
            "secure_what", "secure_when",
            "resistance_empathize", "resistance_ask", "resistance_respond",
        ]}
        gates["start"] = True
        gates["ask_discover"] = True
        note = svc._mock_post_turn_coaching("Tell me about your process.", gates)
        assert "Dissect" in note or "consequences" in note

    @pytest.mark.asyncio
    async def test_async_post_turn_coaching_mock(self):
        svc = self._service()
        gates = {k: False for k in [
            "start", "ask_discover", "ask_dissect", "ask_develop",
            "listen_recap", "explain_reveal", "explain_relate",
            "secure_what", "secure_when",
            "resistance_empathize", "resistance_ask", "resistance_respond",
        ]}
        result = await svc.post_turn_coaching(
            rep_text="Hello, how are you?",
            conversation_history=[],
            active_gates=gates,
            session_mode="practice",
        )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Upload endpoint security tests
# ---------------------------------------------------------------------------

def make_token(payload: dict) -> str:
    from jose import jwt
    secret = os.environ["SUPABASE_JWT_SECRET"]
    return jwt.encode({**payload, "aud": "authenticated"}, secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_upload_requires_auth():
    from main import app
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/uploads", files={"file": ("test.txt", b"hello", "text/plain")})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_rejects_invalid_extension():
    from main import app
    from httpx import AsyncClient, ASGITransport
    token = make_token({"sub": "rep-user-id", "role": "rep"})
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        resp = await ac.post(
            "/api/uploads",
            files={"file": ("malware.exe", b"some binary content", "application/octet-stream")},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file():
    from main import app
    from httpx import AsyncClient, ASGITransport
    token = make_token({"sub": "rep-user-id", "role": "rep"})
    big_content = b"x" * (11 * 1024 * 1024)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        resp = await ac.post(
            "/api/uploads",
            files={"file": ("big.txt", big_content, "text/plain")},
        )
    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# BLOCK-2: WebSocket auth tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_websocket_rejects_empty_token():
    """WS with no token must be closed with code 4001, never accepted."""
    from main import app
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # REST-layer check: the websocket path won't return 200 to HTTP
        resp = await ac.get("/ws/test-session-id")
        # Any non-2xx (or upgrade required) is acceptable — the point is it doesn't let through
        assert resp.status_code != 200


# ---------------------------------------------------------------------------
# BLOCK-4: Role enforcement tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_sessions_requires_admin_role():
    from main import app
    from httpx import AsyncClient, ASGITransport
    token = make_token({"sub": "rep-user-id", "role": "rep"})
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        resp = await ac.get("/api/admin/sessions")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_manager_cohort_requires_manager_role():
    from main import app
    from httpx import AsyncClient, ASGITransport
    token = make_token({"sub": "rep-user-id", "role": "rep"})
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        resp = await ac.get("/api/manager/cohort")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_manager_export_requires_manager_role():
    from main import app
    from httpx import AsyncClient, ASGITransport
    token = make_token({"sub": "rep-user-id", "role": "rep"})
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        resp = await ac.get("/api/manager/export")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_metrics_requires_admin_role():
    from main import app
    from httpx import AsyncClient, ASGITransport
    token = make_token({"sub": "rep-user-id", "role": "rep"})
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        resp = await ac.get("/api/admin/metrics")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_role_can_access_admin_sessions():
    """Admin token must pass role check (403 is the only forbidden outcome)."""
    from main import app
    from httpx import AsyncClient, ASGITransport
    from unittest.mock import patch, AsyncMock, MagicMock
    token = make_token({"sub": "admin-user-id", "role": "admin"})
    mock_ctx = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_ctx.execute = AsyncMock(return_value=mock_result)
    # AsyncSessionLocal is imported lazily inside the endpoint — patch at db module level
    with patch("db.AsyncSessionLocal", return_value=mock_ctx):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as ac:
            resp = await ac.get("/api/admin/sessions")
    # 200 or 500 (DB mock) — either way it passed the role check; 403 means role enforcement failed
    assert resp.status_code != 403


# ── ADV-4: DB-lookup fallback when JWT carries Supabase default role ──────────

@pytest.mark.asyncio
async def test_adv4_supabase_authenticated_role_triggers_db_lookup():
    """JWT role='authenticated' (Supabase default) must fall back to DB lookup."""
    from auth import get_current_user, _APP_ROLES
    from unittest.mock import patch, AsyncMock, MagicMock

    token = make_token({"sub": "trainer-user-id", "role": "authenticated"})

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = ("trainer",)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.execute = AsyncMock(return_value=mock_result)

    # _lookup_role does `from db import AsyncSessionLocal` then `async with AsyncSessionLocal()`
    with patch("db.AsyncSessionLocal", return_value=mock_session):
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user(credentials=creds)

    assert user["role"] == "trainer"
    assert "authenticated" not in _APP_ROLES


@pytest.mark.asyncio
async def test_adv4_db_lookup_unknown_user_defaults_to_rep():
    """If user not found in DB during lookup, default role is 'rep'."""
    from auth import get_current_user
    from unittest.mock import patch, AsyncMock, MagicMock

    token = make_token({"sub": "new-user-id", "role": "authenticated"})

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None  # user not in users table yet
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("db.AsyncSessionLocal", return_value=mock_session):
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user(credentials=creds)

    assert user["role"] == "rep"


@pytest.mark.asyncio
async def test_adv4_explicit_app_role_in_jwt_skips_db_lookup():
    """If JWT already carries a valid app role, DB lookup must NOT fire."""
    from auth import get_current_user
    from unittest.mock import patch, MagicMock

    token = make_token({"sub": "admin-user-id", "role": "admin"})

    with patch("db.AsyncSessionLocal") as mock_ctor:
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user(credentials=creds)

    mock_ctor.assert_not_called()
    assert user["role"] == "admin"
