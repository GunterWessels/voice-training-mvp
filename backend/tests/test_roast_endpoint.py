import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


def get_client():
    from main import app
    return TestClient(app)


MOCK_ROAST = {
    "genre": "Death Metal",
    "genre_emoji": "🤘",
    "character_type": "The Price Dropper",
    "judgment": "He came in with a price and left with a lower one",
    "quote": "I mean, we could probably do something on the cost side.",
    "audio_base64": "ZmFrZWF1ZGlv",
}


def test_roast_endpoint_returns_200_with_valid_session():
    with patch("main.RoastService") as MockService:
        instance = MockService.return_value
        instance.generate = AsyncMock(return_value=MOCK_ROAST)

        client = get_client()
        response = client.post("/sessions/test-session-id/roast")

        assert response.status_code == 200
        data = response.json()
        assert data["genre"] == "Death Metal"
        assert data["audio_base64"] == "ZmFrZWF1ZGlv"
        assert "character_type" in data


def test_roast_endpoint_returns_timeout_on_slow_service():
    async def slow_generate(_):
        await asyncio.sleep(20)
        return MOCK_ROAST

    with patch("main.RoastService") as MockService:
        instance = MockService.return_value
        instance.generate = slow_generate

        client = get_client()
        response = client.post("/sessions/test-session-id/roast")

        assert response.status_code == 408
        assert "timeout" in response.json()["detail"]["error"].lower()
