import os
import uuid
import logging
from typing import Optional
from backend.db import AsyncSessionLocal
from backend.models import MeteringEvent

COST_TABLE = {
    ("openai", "gpt-4o-mini"): {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    ("openai", "tts-1"):        {"chars": 0.015 / 1000},
    ("elevenlabs", None):       {"chars": 0.18 / 1000},
    ("anthropic", "claude-3-haiku-20240307"): {"input": 0.25 / 1_000_000, "output": 1.25 / 1_000_000},
}

_DEFAULT_BUDGET_CAPS = {
    "quick_drill":   0.40,
    "full_practice": 1.00,
    "cert_run":      2.00,
}

def compute_cost(provider: str, model: Optional[str], tokens_in: int = 0,
                 tokens_out: int = 0, characters: int = 0) -> float:
    key = (provider, model)
    rates = COST_TABLE.get(key) or COST_TABLE.get((provider, None)) or {}
    cost = 0.0
    if "input" in rates:
        cost += tokens_in * rates["input"] + tokens_out * rates["output"]
    if "chars" in rates:
        cost += characters * rates["chars"]
    return round(cost, 6)

async def write_event(session_id: str, user_id: str, cohort_id: Optional[str],
                      division_id: Optional[str], provider: str, model: Optional[str],
                      call_type: str, tokens_in: int = 0, tokens_out: int = 0,
                      characters: int = 0) -> None:
    cost = compute_cost(provider, model, tokens_in, tokens_out, characters)
    try:
        async with AsyncSessionLocal() as db:
            event = MeteringEvent(
                session_id=uuid.UUID(session_id),
                user_id=uuid.UUID(user_id) if user_id else None,
                cohort_id=uuid.UUID(cohort_id) if cohort_id else None,
                division_id=uuid.UUID(division_id) if division_id else None,
                provider=provider, model=model,
                call_type=call_type, tokens_in=tokens_in, tokens_out=tokens_out,
                cost_usd=cost,
            )
            db.add(event)
            await db.commit()
    except Exception as e:
        logging.warning("metering write_event failed: %s", e)

async def get_session_cost(session_id: str) -> float:
    import uuid as _uuid
    from sqlalchemy import select, func
    # MeteringEvent.session_id is UUID(as_uuid=True); asyncpg requires a uuid.UUID object
    try:
        session_uuid = _uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    except (ValueError, AttributeError):
        session_uuid = session_id
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.sum(MeteringEvent.cost_usd))
            .where(MeteringEvent.session_id == session_uuid)
        )
        return float(result.scalar() or 0)

def is_over_budget(current_cost: float, preset: str) -> bool:
    caps = {
        "quick_drill":   float(os.environ.get("TOKEN_BUDGET_QUICK_DRILL", "0.40")),
        "full_practice": float(os.environ.get("TOKEN_BUDGET_FULL_PRACTICE", "1.00")),
        "cert_run":      float(os.environ.get("TOKEN_BUDGET_CERT_RUN", "2.00")),
    }
    return current_cost >= caps.get(preset, caps["full_practice"])
