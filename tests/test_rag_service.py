import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_retrieve_returns_list():
    from backend.rag_service import retrieve
    # execute() is async; CursorResult.fetchall() is synchronous — use MagicMock for cursor
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_cursor)
    with patch("backend.rag_service.embed_query", new_callable=AsyncMock, return_value=[0.1]*1536):
        results = await retrieve("test query", scenario_id="abc", domain="product", db=mock_db)
    assert isinstance(results, list)

def test_arc_stage_triggers_retrieval():
    from backend.rag_service import should_retrieve_for_stage
    assert should_retrieve_for_stage(1) is False
    assert should_retrieve_for_stage(2) is False
    assert should_retrieve_for_stage(3) is True
    assert should_retrieve_for_stage(4) is True
    assert should_retrieve_for_stage(5) is True
    assert should_retrieve_for_stage(6) is False
