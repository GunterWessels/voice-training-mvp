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
            json={"persona_id": "cfo", "scenario_id": "00000000-0000-0000-0000-000000000000"})
        for _ in range(25)
    ]
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes, f"Expected 429, got: {set(status_codes)}"
