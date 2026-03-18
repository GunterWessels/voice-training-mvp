import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch


def make_messages(lines):
    return [{"speaker": s, "text": t} for s, t in lines]


VALID_CLAUDE_JSON = json.dumps({
    "genre": "Death Metal",
    "genre_emoji": "🤘",
    "character_type": "The Price Dropper",
    "judgment": "He came in with a price and left with a lower one",
    "quote": "I mean, we could probably do something on the cost side.",
    "tts_script": "He came in with a price... he left with a lower one. Nobody asked. 'I mean, we could probably do something on the cost side.' The Price Dropper. On Death Metal."
})


def test_format_transcript():
    from roast_service import RoastService
    svc = RoastService.__new__(RoastService)
    messages = make_messages([
        ("user", "Hello, I wanted to discuss pricing."),
        ("ai", "What's your budget?"),
        ("user", "We could probably do something on the cost side."),
    ])
    result = svc._format_transcript(messages)
    assert "Rep: Hello, I wanted to discuss pricing." in result
    assert "Buyer: What's your budget?" in result
    assert "Rep: We could probably do something on the cost side." in result


def test_parse_claude_response_valid():
    from roast_service import RoastService
    svc = RoastService.__new__(RoastService)
    result = svc._parse_claude_response(VALID_CLAUDE_JSON)
    assert result["genre"] == "Death Metal"
    assert result["character_type"] == "The Price Dropper"
    assert "tts_script" in result


def test_parse_claude_response_with_markdown_fence():
    from roast_service import RoastService
    svc = RoastService.__new__(RoastService)
    wrapped = f"```json\n{VALID_CLAUDE_JSON}\n```"
    result = svc._parse_claude_response(wrapped)
    assert result["genre"] == "Death Metal"


def test_parse_claude_response_returns_fallback_on_garbage():
    from roast_service import RoastService
    svc = RoastService.__new__(RoastService)
    result = svc._parse_claude_response("not json at all lol")
    assert result["genre"] == "Elevator Bossa Nova"
    assert result["character_type"] == "The Mystery Rep"
    assert result.get("audio_base64") is None


def test_parse_claude_response_returns_fallback_on_missing_fields():
    from roast_service import RoastService
    svc = RoastService.__new__(RoastService)
    result = svc._parse_claude_response('{"genre": "Death Metal"}')
    assert result["character_type"] == "The Mystery Rep"


@pytest.mark.asyncio
async def test_generate_returns_result_with_audio():
    from roast_service import RoastService
    svc = RoastService.__new__(RoastService)
    mock_db = MagicMock()
    mock_db.get_messages.return_value = make_messages([
        ("user", "We could probably do something on the cost side."),
        ("ai", "What is your budget?"),
    ])
    svc.db = mock_db
    mock_ai = MagicMock()
    mock_ai.provider = "openai"
    mock_ai._call_provider = AsyncMock(return_value=VALID_CLAUDE_JSON)
    svc.ai_service = mock_ai
    mock_el = MagicMock()
    mock_el.text_to_speech = AsyncMock(return_value=b"fakeaudiobytes")
    svc.elevenlabs = mock_el
    result = await svc.generate("session-abc")
    assert result["genre"] == "Death Metal"
    assert result["audio_base64"] is not None
    import base64
    decoded = base64.b64decode(result["audio_base64"])
    assert decoded == b"fakeaudiobytes"


@pytest.mark.asyncio
async def test_generate_returns_fallback_when_elevenlabs_fails():
    from roast_service import RoastService
    svc = RoastService.__new__(RoastService)
    mock_db = MagicMock()
    mock_db.get_messages.return_value = make_messages([("user", "Hi")])
    svc.db = mock_db
    mock_ai = MagicMock()
    mock_ai.provider = "openai"
    mock_ai._call_provider = AsyncMock(return_value=VALID_CLAUDE_JSON)
    svc.ai_service = mock_ai
    mock_el = MagicMock()
    mock_el.text_to_speech = AsyncMock(return_value=None)
    svc.elevenlabs = mock_el
    result = await svc.generate("session-abc")
    assert result["genre"] == "Death Metal"
    assert result["audio_base64"] is None


@pytest.mark.asyncio
async def test_generate_returns_fallback_when_no_messages():
    from roast_service import RoastService
    svc = RoastService.__new__(RoastService)
    mock_db = MagicMock()
    mock_db.get_messages.return_value = []
    svc.db = mock_db
    svc.ai_service = MagicMock()
    svc.elevenlabs = MagicMock()
    result = await svc.generate("session-empty")
    assert result["character_type"] == "The Mystery Rep"
