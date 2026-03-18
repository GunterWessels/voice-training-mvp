"""Integration tests: session lifecycle via /api/sessions endpoints."""
import pytest
import pytest_asyncio


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_and_retrieve_session(async_client, valid_jwt, tria_scenario_id):
    """POST /api/sessions → 201 with session_id; GET /api/sessions/{id} → 200 with arc_stage_reached."""
    headers = {"Authorization": f"Bearer {valid_jwt}"}

    # Create session
    response = await async_client.post(
        "/api/sessions",
        json={
            "persona_id": "vac_buyer",
            "scenario_id": tria_scenario_id,
            "preset": "full_practice",
        },
        headers=headers,
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    body = response.json()
    assert "session_id" in body
    session_id = body["session_id"]
    assert session_id  # non-empty string

    # Retrieve session
    response = await async_client.get(
        f"/api/sessions/{session_id}",
        headers=headers,
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    session_body = response.json()
    assert "arc_stage_reached" in session_body
    assert session_body["session_id"] == session_id
    assert session_body["arc_stage_reached"] == 1
    assert session_body["status"] == "in_progress"
    assert session_body["preset"] == "full_practice"
