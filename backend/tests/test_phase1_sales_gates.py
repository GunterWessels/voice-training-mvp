"""Phase 1 tests — SALES gate detection and post_turn_coaching.

These tests run without a live database or AI API.
"""
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
    """Build a minimal conversation history with the given rep lines."""
    return [{"speaker": "user", "text": line} for line in rep_lines]


class TestSalesGateDetection:
    ev = ConditionEvaluator()

    def test_start_detected(self):
        h = _history("The reason for my call today is to show you something that saves OR time.")
        flags = self.ev.sales_flags(h)
        assert flags["start"] is True

    def test_start_not_triggered_by_generic_opener(self):
        h = _history("Hello, how are you?")
        flags = self.ev.sales_flags(h)
        assert flags["start"] is False

    def test_ask_discover(self):
        h = _history("What challenges do you face with your current stent change-out process?")
        flags = self.ev.sales_flags(h)
        assert flags["ask_discover"] is True

    def test_ask_dissect(self):
        h = _history("How does that impact your patient throughput in the OR?")
        flags = self.ev.sales_flags(h)
        assert flags["ask_dissect"] is True

    def test_ask_develop(self):
        h = _history("How would it help if you could eliminate re-interventions in the first 90 days?")
        flags = self.ev.sales_flags(h)
        assert flags["ask_develop"] is True

    def test_listen_recap(self):
        h = _history("So what I'm hearing is that your main concern is re-intervention rates. Is that right?")
        flags = self.ev.sales_flags(h)
        assert flags["listen_recap"] is True

    def test_explain_reveal(self):
        h = _history("Clinical data indicates a 94% patency rate at 12 months with this design.")
        flags = self.ev.sales_flags(h)
        assert flags["explain_reveal"] is True

    def test_explain_relate(self):
        h = _history("Given what you told me about OR scheduling pressure, this matters directly.")
        flags = self.ev.sales_flags(h)
        assert flags["explain_relate"] is True

    def test_secure_what(self):
        h = _history("Can we schedule a 30-minute VAC presentation for your team?")
        flags = self.ev.sales_flags(h)
        assert flags["secure_what"] is True

    def test_secure_when(self):
        h = _history("I'll have the proposal to you by Friday.")
        flags = self.ev.sales_flags(h)
        assert flags["secure_when"] is True

    def test_resistance_empathize(self):
        h = _history("I understand — that's a fair concern about upfront cost.")
        flags = self.ev.sales_flags(h)
        assert flags["resistance_empathize"] is True

    def test_resistance_ask(self):
        h = _history("Help me understand what's driving that concern about switching vendors.")
        flags = self.ev.sales_flags(h)
        assert flags["resistance_ask"] is True

    def test_resistance_respond(self):
        h = _history("Let me address that directly — here's what the data on changeover time shows.")
        flags = self.ev.sales_flags(h)
        assert flags["resistance_respond"] is True

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
        # start + explain_reveal + explain_relate + secure_what + secure_when
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
        history = _history("The reason for my call is to share clinical evidence on patient outcomes.")
        tracker.evaluate(history)
        assert tracker.sales_flags["start"] is True
        assert tracker.sales_flags["explain_reveal"] is True


# ---------------------------------------------------------------------------
# post_turn_coaching mock tests
# ---------------------------------------------------------------------------
from ai_service import AIService


class TestPostTurnCoachingMock:
    """Tests run against the mock provider (no API key required)."""

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
        assert len(note.split()) <= 15  # reasonable sentence

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
# Upload endpoint tests
# ---------------------------------------------------------------------------
import io


def make_token(payload: dict) -> str:
    from jose import jwt
    secret = os.environ["SUPABASE_JWT_SECRET"]
    return jwt.encode({**payload, "aud": "authenticated"}, secret, algorithm="HS256")


@pytest.fixture
async def rep_client():
    from main import app
    from httpx import AsyncClient, ASGITransport
    token = make_token({"sub": "rep-user-id", "role": "rep"})
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_upload_requires_auth():
    from main import app
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/uploads", files={"file": ("test.txt", b"hello", "text/plain")})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_rejects_invalid_extension(rep_client):
    content = b"some binary content"
    resp = await rep_client.post(
        "/api/uploads",
        files={"file": ("malware.exe", content, "application/octet-stream")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(rep_client):
    # 11MB of zeros — exceeds 10MB limit
    big_content = b"x" * (11 * 1024 * 1024)
    resp = await rep_client.post(
        "/api/uploads",
        files={"file": ("big.txt", big_content, "text/plain")},
    )
    assert resp.status_code == 413
