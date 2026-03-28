import asyncio
import pytest
from unittest.mock import AsyncMock, patch


def _run_async(coro):
    """Run a coroutine to completion in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def sync_seeded_scenario():
    """Synchronous wrapper: seeds a test scenario into PostgreSQL and yields its ID.
    Uses a fresh event loop so it can be consumed by a sync test function.
    """
    import uuid
    from db import AsyncSessionLocal
    from models import Scenario, Division

    async def _seed():
        async with AsyncSessionLocal() as db:
            div = Division(name="WS Test Division", slug=f"ws-test-{uuid.uuid4().hex[:8]}")
            db.add(div)
            await db.flush()
            scenario = Scenario(
                name="WS Test Scenario",
                division_id=div.id,
                product_name="TRIA Laser System",
                persona_id="vac_buyer",
                arc={"stages": [
                    {"id": 1, "name": "DISCOVERY",
                     "persona_instruction": "Be vague. Don't commit.",
                     "unlock_condition": "open_ended_questions >= 2",
                     "max_turns": 6},
                    {"id": 2, "name": "VALUE_BUILDING",
                     "persona_instruction": "Show some interest.",
                     "unlock_condition": "cof_clinical_mentioned == true",
                     "max_turns": 6},
                ]},
            )
            db.add(scenario)
            await db.commit()
            return {"scenario_id": str(scenario.id), "division_id": str(div.id)}

    return _run_async(_seed())


def test_websocket_arc_stage_advances(client, valid_jwt, sync_seeded_scenario):
    # Mock ai_service so the test does not call real OpenAI (CI uses sk-test which fails auth)
    mock_ai_response = {
        "text": "That's a meaningful question about our clinical workflow.",
        "audio": None,
        "tts_provider": "none",
    }
    with patch("main.ai_service.generate_response_with_audio",
               new_callable=AsyncMock, return_value=mock_ai_response):
        # Create a new PostgreSQL-backed session via POST /api/sessions
        resp = client.post("/api/sessions",
            json={"persona_id": "vac_buyer", "scenario_id": sync_seeded_scenario["scenario_id"]},
            headers={"Authorization": f"Bearer {valid_jwt}"})
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]

        with client.websocket_connect(f"/ws/{session_id}?token={valid_jwt}") as ws:
            ws.receive_json()  # ready message
            ws.receive_json()  # greeting
            # First open-ended question (stage still 1 — needs 2 to unlock)
            ws.send_json({"type": "user_message",
                          "text": "What challenges are you seeing with patient outcomes from stone management?"})
            response = ws.receive_json()
            assert response["type"] == "ai_message"
            # Second open-ended question — meets unlock condition for stage 1
            ws.send_json({"type": "user_message",
                          "text": "How does that impact your OR scheduling throughput?"})
            ws.receive_json()
        # After WS closes, verify arc stage advanced in DB
        detail = client.get(f"/api/sessions/{session_id}",
                            headers={"Authorization": f"Bearer {valid_jwt}"})
        assert detail.json()["arc_stage_reached"] >= 2
