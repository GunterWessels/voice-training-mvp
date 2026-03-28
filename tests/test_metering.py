import pytest

def test_openai_cost_calculated_correctly():
    from metering import compute_cost
    cost = compute_cost(provider="openai", model="gpt-4o-mini", tokens_in=1000, tokens_out=500)
    expected = (1000 * 0.15 / 1_000_000) + (500 * 0.60 / 1_000_000)
    assert abs(cost - expected) < 0.0000001

def test_elevenlabs_cost_calculated_correctly():
    from metering import compute_cost
    cost = compute_cost(provider="elevenlabs", model=None, tokens_in=0, tokens_out=0, characters=200)
    expected = 200 * 0.18 / 1000
    assert abs(cost - expected) < 0.0000001

@pytest.mark.asyncio
async def test_session_cost_rollup(seeded_metering_session):
    from metering import get_session_cost
    total = await get_session_cost(seeded_metering_session)
    assert total == pytest.approx(0.045, abs=0.001)

def test_token_budget_cap_enforced():
    from metering import is_over_budget
    assert is_over_budget(current_cost=0.41, preset="quick_drill") is True
    assert is_over_budget(current_cost=0.39, preset="quick_drill") is False
