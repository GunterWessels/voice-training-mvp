import os
import pytest
from sqlalchemy import text
from backend.db import engine

@pytest.mark.asyncio
async def test_all_tables_exist():
    tables = ["divisions", "cohorts", "users", "scenarios", "sessions",
              "messages", "completions", "metering_events",
              "practice_series", "practice_series_items"]
    async with engine.connect() as conn:
        for table in tables:
            result = await conn.execute(
                text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
                {"t": table}
            )
            assert result.fetchone() is not None, f"Table {table} missing"
