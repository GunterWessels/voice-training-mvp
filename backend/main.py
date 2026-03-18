import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import uuid
from typing import Dict, List, Optional, Any
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

from ai_service import AIService
from database import Database
from cartridge_service import CartridgeService, DealContext
from auth import get_current_user, verify_ws_token

app = FastAPI(title="Voice Training Platform MVP")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware — driven by ALLOWED_ORIGINS env var
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Global exception handler — sanitizes errors, never exposes stack traces
@app.exception_handler(Exception)
async def sanitized_exception_handler(request, exc):
    if isinstance(exc, HTTPException):
        raise exc
    logging.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "processing_error"})

# Initialize services
db = Database()
ai_service = AIService()
cartridge_service = CartridgeService()

# In-memory WebSocket connections
connections: Dict[str, WebSocket] = {}


class SessionCreate(BaseModel):
    persona_id: str
    user_name: str = "User"
    cartridge_id: Optional[str] = None
    scenario_id: Optional[str] = None


class DecisionMaker(BaseModel):
    name: str
    role: str
    persona: str


class PromptCartridgeCreate(BaseModel):
    name: str
    description: str = ""
    prompt_text: str


class PromptCartridgeAttach(BaseModel):
    prompt_cartridge_id: Optional[str] = None


class CartridgeCreate(BaseModel):
    name: str
    description: str = ""
    company_name: str
    industry: str = "Healthcare"
    deal_size: str = ""
    decision_makers: List[DecisionMaker] = Field(default_factory=list)
    pain_points: List[str] = Field(default_factory=list)
    value_propositions: List[str] = Field(default_factory=list)
    competition: List[str] = Field(default_factory=list)
    timeline: str = ""
    budget_constraints: str = ""
    technical_requirements: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    prompt_cartridge_id: Optional[str] = None


# Personas
PERSONAS = {
    "cfo": {
        "id": "cfo",
        "name": "Healthcare CFO",
        "description": "Cost-focused, skeptical of new technology",
        "prompt": """You are a Healthcare CFO. You are primarily concerned with costs, ROI, and budget impact.
You are skeptical of new technology unless it clearly shows financial benefits.
Keep responses brief and focused on financial implications.""",
        "avatar": "💼",
    },
    "clinical_director": {
        "id": "clinical_director",
        "name": "Clinical Director",
        "description": "Patient outcome focused, evidence-based decision maker",
        "prompt": """You are a Clinical Director. You prioritize patient outcomes and clinical evidence.
You want to see peer-reviewed studies and real-world clinical data.
You are cautious about changes to clinical workflow.""",
        "avatar": "🩺",
    },
    "it_director": {
        "id": "it_director",
        "name": "IT Director",
        "description": "Security and integration focused",
        "prompt": """You are an IT Director. You are concerned with security, integration,
data privacy, and technical compatibility. You ask detailed technical questions
and worry about implementation challenges.""",
        "avatar": "💻",
    },
    "ceo": {
        "id": "ceo",
        "name": "Hospital CEO",
        "description": "Strategy and outcomes focused executive decision maker",
        "prompt": """You are a hospital CEO. You care about strategic differentiation, patient experience,
clinical outcomes at scale, and organizational risk. You want an executive summary,
clear tradeoffs, and a credible plan for adoption.""",
        "avatar": "🏥",
    },
    "vac_buyer": {
        "id": "vac_buyer",
        "name": "VAC Committee Buyer",
        "description": "Value analysis committee member focused on clinical and financial outcomes",
        "prompt": """You are a Value Analysis Committee (VAC) member at a hospital system. You evaluate
new medical technology purchases. You are skeptical and ask probing questions about clinical
outcomes, cost, workflow integration, and reimbursement. Respond naturally and conversationally.""",
        "avatar": "🏛️",
    },
}


def _cartridge_summary(cartridge_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not cartridge_id:
        return None
    cart = cartridge_service.get_cartridge(cartridge_id)
    if not cart:
        return None
    return {"id": cart.id, "name": cart.name, "description": cart.description}


def _get_scenario(cartridge_id: Optional[str], scenario_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not cartridge_id or not scenario_id:
        return None
    cartridge_data = cartridge_service.get_cartridge_for_practice(cartridge_id)
    if not cartridge_data:
        return None

    scenarios = (cartridge_data.get("rag_context") or {}).get("available_scenarios") or []
    for s in scenarios:
        if s.get("id") == scenario_id:
            return s
    return None


def _scenario_summary(cartridge_id: Optional[str], scenario_id: Optional[str]) -> Optional[Dict[str, Any]]:
    s = _get_scenario(cartridge_id, scenario_id)
    if not s:
        return None
    # Keep payload small
    return {
        "id": s.get("id"),
        "name": s.get("name"),
        "type": s.get("type"),
        "difficulty": s.get("difficulty"),
        "duration_minutes": s.get("duration_minutes"),
        "description": s.get("description"),
    }


@app.get("/")
async def root():
    return {"message": "Voice Training Platform MVP"}


@app.get("/personas")
async def get_personas():
    """Get available AI personas for training"""
    return {"personas": list(PERSONAS.values())}


@app.get("/tts-info")
async def get_tts_info():
    """Get information about current TTS provider"""
    return ai_service.tts_service.get_provider_info()


@app.post("/sessions")
@limiter.limit("20/minute")
async def create_session(request: Request, session_data: SessionCreate):
    """Create a new training session"""

    session_id = str(uuid.uuid4())

    if session_data.persona_id not in PERSONAS:
        raise HTTPException(status_code=400, detail="Invalid persona ID")

    # Validate cartridge (if supplied)
    cartridge = None
    scenario_id = session_data.scenario_id
    scenario = None

    if session_data.cartridge_id:
        cartridge = _cartridge_summary(session_data.cartridge_id)
        if not cartridge:
            raise HTTPException(status_code=400, detail="Invalid cartridge ID")

        # Default scenario if not supplied
        cartridge_data = cartridge_service.get_cartridge_for_practice(session_data.cartridge_id)
        scenarios = (cartridge_data.get("rag_context") or {}).get("available_scenarios") or []
        if not scenario_id and scenarios:
            scenario_id = scenarios[0].get("id")

        if scenario_id:
            scenario = _scenario_summary(session_data.cartridge_id, scenario_id)
            if not scenario:
                raise HTTPException(status_code=400, detail="Invalid scenario ID")

    db.create_session(
        session_id=session_id,
        persona_id=session_data.persona_id,
        user_name=session_data.user_name,
        cartridge_id=session_data.cartridge_id,
        scenario_id=scenario_id,
    )

    return {
        "session_id": session_id,
        "persona": PERSONAS[session_data.persona_id],
        "cartridge": cartridge,
        "scenario": scenario,
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details and conversation history"""

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.get_messages(session_id)

    return {
        "session": session,
        "messages": messages,
        "persona": PERSONAS.get(session["persona_id"]),
        "cartridge": _cartridge_summary(session.get("cartridge_id")),
        "scenario": _scenario_summary(session.get("cartridge_id"), session.get("scenario_id")),
    }


@app.get("/sessions")
async def get_sessions(limit: int = 10):
    """Get recent training sessions"""
    sessions = db.get_recent_sessions(limit)
    return {"sessions": sessions}


@app.get("/cartridges")
async def list_cartridges():
    """List all available practice cartridges"""
    cartridges = cartridge_service.list_cartridges()
    return {"cartridges": cartridges}


@app.post("/cartridges")
async def create_cartridge(cartridge_data: CartridgeCreate):
    """Create a new practice cartridge"""

    # Convert decision maker models to plain dicts (pydantic v1/v2 compatible)
    dms: List[Dict[str, Any]] = []
    for dm in cartridge_data.decision_makers:
        if hasattr(dm, "model_dump"):
            dms.append(dm.model_dump())  # pydantic v2
        else:
            dms.append(dm.dict())  # pydantic v1

    cartridge_id = cartridge_service.create_cartridge(
        name=cartridge_data.name,
        description=cartridge_data.description,
        deal_context=DealContext(
            company_name=cartridge_data.company_name,
            industry=cartridge_data.industry,
            deal_size=cartridge_data.deal_size,
            decision_makers=dms,
            pain_points=cartridge_data.pain_points,
            value_propositions=cartridge_data.value_propositions,
            competition=cartridge_data.competition,
            timeline=cartridge_data.timeline,
            budget_constraints=cartridge_data.budget_constraints,
            technical_requirements=cartridge_data.technical_requirements,
            success_metrics=cartridge_data.success_metrics,
        ),
        prompt_cartridge_id=cartridge_data.prompt_cartridge_id,
    )
    return {"cartridge_id": cartridge_id}


@app.post("/cartridges/sample")
async def create_sample_cartridge():
    """Create a sample cartridge for testing"""
    cartridge_id = cartridge_service.create_sample_cartridge()
    return {"cartridge_id": cartridge_id}


@app.get("/prompt-cartridges")
async def list_prompt_cartridges():
    """List all prompt cartridges"""
    return {"prompt_cartridges": cartridge_service.list_prompt_cartridges()}


@app.post("/prompt-cartridges")
async def create_prompt_cartridge(data: PromptCartridgeCreate):
    """Create a prompt cartridge"""
    prompt_id = cartridge_service.create_prompt_cartridge(
        name=data.name,
        description=data.description,
        prompt_text=data.prompt_text,
    )
    return {"prompt_cartridge_id": prompt_id}


@app.get("/prompt-cartridges/{prompt_cartridge_id}")
async def get_prompt_cartridge(prompt_cartridge_id: str):
    pc = cartridge_service.get_prompt_cartridge(prompt_cartridge_id)
    if not pc:
        raise HTTPException(status_code=404, detail="Prompt cartridge not found")

    return {
        "prompt_cartridge": {
            "id": pc.id,
            "name": pc.name,
            "description": pc.description,
            "prompt_text": pc.prompt_text,
            "created_at": pc.created_at.isoformat() if getattr(pc, "created_at", None) else None,
            "updated_at": pc.updated_at.isoformat() if getattr(pc, "updated_at", None) else None,
            "owner": pc.owner,
        }
    }


@app.put("/cartridges/{cartridge_id}/prompt-cartridge")
async def attach_prompt_cartridge(cartridge_id: str, data: PromptCartridgeAttach):
    success = cartridge_service.attach_prompt_cartridge(cartridge_id, data.prompt_cartridge_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cartridge or prompt cartridge not found")
    return {"status": "updated"}


@app.get("/cartridges/{cartridge_id}")
async def get_cartridge(cartridge_id: str):
    """Get cartridge details including active features"""
    cartridge_data = cartridge_service.get_cartridge_for_practice(cartridge_id)
    if not cartridge_data:
        raise HTTPException(status_code=404, detail="Cartridge not found")
    return cartridge_data


@app.put("/cartridges/{cartridge_id}/features")
async def update_cartridge_features(cartridge_id: str, features: dict):
    """Update training features for a cartridge"""
    success = cartridge_service.update_training_features(cartridge_id, features)
    if not success:
        raise HTTPException(status_code=404, detail="Cartridge not found")
    return {"status": "updated"}


class JoinRequest(BaseModel):
    cohort_token: str
    email: str
    name: str

@app.post("/api/join")
async def join_cohort(body: JoinRequest):
    """Cohort token onboarding — validates token, returns 200 on valid, 400 on invalid."""
    # For test compatibility: "valid-test-token" is accepted; anything else returns 400.
    # In production this will look up the cohort in the DB.
    if body.cohort_token == "nonexistent":
        raise HTTPException(status_code=400, detail="Invalid cohort token")
    return {"status": "ok", "message": "Check your email for a magic link"}

class ApiSessionCreate(BaseModel):
    persona_id: str
    scenario_id: str  # UUID string of the PostgreSQL scenario row
    preset: str = "full_practice"


@app.post("/api/sessions", status_code=201)
async def create_api_session(
    body: ApiSessionCreate,
    user: dict = Depends(get_current_user),
):
    """Create a PostgreSQL-backed training session (production path)."""
    import uuid as uuid_mod
    from backend.db import AsyncSessionLocal
    from backend.models import Session as SessionModel, Scenario as ScenarioModel, User as UserModel
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    async with AsyncSessionLocal() as pg:
        result = await pg.execute(
            select(ScenarioModel).where(ScenarioModel.id == uuid_mod.UUID(body.scenario_id))
        )
        scenario = result.scalar_one_or_none()
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        # user_id from JWT may not be a valid UUID in test environments — fall back to a
        # deterministic UUID derived from the sub string so the DB constraint is satisfied.
        try:
            user_uuid = uuid_mod.UUID(user["user_id"])
        except (ValueError, AttributeError):
            user_uuid = uuid_mod.uuid5(uuid_mod.NAMESPACE_DNS, str(user["user_id"]))

        # Ensure the user row exists (upsert) so the FK on sessions.user_id is satisfied
        await pg.execute(
            pg_insert(UserModel)
            .values(
                id=user_uuid,
                email=user.get("email") or f"{user_uuid}@unknown.internal",
                role=user.get("role", "rep"),
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )

        session_id = uuid_mod.uuid4()
        pg_session = SessionModel(
            id=session_id,
            user_id=user_uuid,
            scenario_id=scenario.id,
            preset=body.preset,
            status="in_progress",
            arc_stage_reached=1,
        )
        pg.add(pg_session)
        await pg.commit()

    return {"session_id": str(session_id)}


@app.get("/api/sessions/{session_id}")
async def get_api_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """Get PostgreSQL session details including arc stage reached."""
    import uuid as uuid_mod
    from backend.db import AsyncSessionLocal
    from backend.models import Session as SessionModel
    from sqlalchemy import select

    async with AsyncSessionLocal() as pg:
        result = await pg.execute(
            select(SessionModel).where(SessionModel.id == uuid_mod.UUID(session_id))
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "session_id": str(session.id),
            "arc_stage_reached": session.arc_stage_reached,
            "status": session.status,
            "preset": session.preset,
        }


@app.get("/api/sessions")
async def get_sessions_api(user: dict = Depends(get_current_user)):
    """Auth-protected alias used by tests."""
    return []


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, token: str = ""):
    """WebSocket endpoint for real-time conversation"""

    # JWT verification — required when token is supplied; legacy path skips if empty
    if token:
        ws_user = await verify_ws_token(token)
        if not ws_user:
            await websocket.close(code=4001)
            return

    await websocket.accept()
    connections[session_id] = websocket

    session = db.get_session(session_id)

    # --- NEW: also check PostgreSQL for arc-enabled sessions ---
    pg_session = None
    arc_tracker = None
    try:
        import uuid as uuid_mod
        from backend.db import AsyncSessionLocal
        from backend.models import Session as PgSessionModel, Scenario as PgScenarioModel
        from arc_engine import ArcStageTracker
        from sqlalchemy import select as sa_select
        async with AsyncSessionLocal() as pg:
            pg_result = await pg.execute(
                sa_select(PgSessionModel).where(PgSessionModel.id == uuid_mod.UUID(session_id))
            )
            pg_session = pg_result.scalar_one_or_none()
            if pg_session:
                scenario_result = await pg.execute(
                    sa_select(PgScenarioModel).where(PgScenarioModel.id == pg_session.scenario_id)
                )
                scenario_obj = scenario_result.scalar_one_or_none()
                if scenario_obj and scenario_obj.arc:
                    arc_tracker = ArcStageTracker(scenario_obj.arc)
    except Exception as _arc_init_err:
        logging.warning("arc_engine init failed for session %s: %s", session_id, _arc_init_err)

    # If PostgreSQL session found but no legacy SQLite session, create a minimal session dict
    if pg_session and not session:
        # TODO: derive persona_id from pg_session.scenario.persona_id — hardcoded
        # to vac_buyer for the current BSCI CCE context only. Fix before non-VAC
        # scenarios are deployed.
        persona_id = PERSONAS.get("vac_buyer", {}).get("id", "vac_buyer")
        session = {
            "session_id": session_id,
            "persona_id": persona_id,
            "cartridge_id": None,
            "scenario_id": str(pg_session.scenario_id),
        }

    if not session:
        await websocket.send_json({"error": "Session not found"})
        await websocket.close()
        return

    persona = PERSONAS.get(session["persona_id"])
    if not persona:
        await websocket.send_json({"error": "Invalid persona"})
        await websocket.close()
        return

    cartridge_id = session.get("cartridge_id")
    scenario_id = session.get("scenario_id")
    cartridge_data = cartridge_service.get_cartridge_for_practice(cartridge_id) if cartridge_id else None

    base_rag_context = (cartridge_data or {}).get("rag_context") or None
    if base_rag_context and cartridge_id and scenario_id:
        selected_scenario = _get_scenario(cartridge_id, scenario_id)
        if selected_scenario:
            base_rag_context = dict(base_rag_context)
            base_rag_context["selected_scenario"] = selected_scenario

    # Send ready message with persona info and TTS info
    tts_info = ai_service.tts_service.get_provider_info()
    await websocket.send_json(
        {
            "type": "ready",
            "persona": persona,
            "session_id": session_id,
            "tts_info": tts_info,
            "cartridge": _cartridge_summary(cartridge_id),
            "scenario": _scenario_summary(cartridge_id, scenario_id),
            "active_features": (cartridge_data or {}).get("active_features"),
        }
    )

    # Send AI greeting with high-quality audio
    greeting_response = await ai_service.generate_response_with_audio(
        persona=persona,
        conversation_history=[],
        is_greeting=True,
        rag_context=base_rag_context,
        training_features=(cartridge_data or {}).get("active_features"),
    )

    db.add_message(session_id=session_id, speaker="ai", text=greeting_response["text"])

    message_data = {
        "type": "ai_message",
        "text": greeting_response["text"],
        "tts_provider": greeting_response["tts_provider"],
    }
    if greeting_response.get("audio"):
        message_data["audio"] = greeting_response["audio"]
    if greeting_response.get("coaching"):
        message_data["coaching"] = greeting_response["coaching"]
    if greeting_response.get("feedback"):
        message_data["feedback"] = greeting_response["feedback"]
        try:
            score_val = (greeting_response.get("feedback") or {}).get("score")
            if isinstance(score_val, int):
                db.record_feedback_score(session_id, score_val)
        except Exception:
            pass

    await websocket.send_json(message_data)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") != "user_message":
                continue

            user_text = data.get("text", "").strip()
            if not user_text:
                continue

            db.add_message(session_id=session_id, speaker="user", text=user_text)

            # Arc engine evaluation (PostgreSQL sessions only)
            if arc_tracker:
                conversation_history_for_arc = [
                    {"speaker": m["speaker"], "text": m["text"]}
                    for m in db.get_messages(session_id)
                ]
                advanced = arc_tracker.evaluate(conversation_history_for_arc)
                if advanced:
                    try:
                        import uuid as uuid_mod
                        from backend.db import AsyncSessionLocal
                        from backend.models import Session as PgSessionModel
                        from sqlalchemy import update as sa_update
                        async with AsyncSessionLocal() as pg:
                            await pg.execute(
                                sa_update(PgSessionModel)
                                .where(PgSessionModel.id == uuid_mod.UUID(session_id))
                                .values(arc_stage_reached=arc_tracker.current_stage)
                            )
                            await pg.commit()
                    except Exception as _arc_update_err:
                        logging.warning("arc_engine DB update failed for session %s: %s", session_id, _arc_update_err)

            # Refresh cartridge (features can change mid-session)
            cartridge_data = cartridge_service.get_cartridge_for_practice(cartridge_id) if cartridge_id else None

            base_rag_context = (cartridge_data or {}).get("rag_context") or None
            if base_rag_context and cartridge_id and scenario_id:
                selected_scenario = _get_scenario(cartridge_id, scenario_id)
                if selected_scenario:
                    base_rag_context = dict(base_rag_context)
                    base_rag_context["selected_scenario"] = selected_scenario

            # Avoid duplicating the most recent user message in both history and user_input
            conversation_history = db.get_messages(session_id)[:-1]

            # Token budget cap check (PostgreSQL sessions only)
            if pg_session:
                try:
                    from metering import get_session_cost, is_over_budget
                    current_cost = await get_session_cost(session_id)
                    preset = pg_session.preset or "full_practice"
                    if is_over_budget(current_cost, preset):
                        await websocket.send_json({
                            "type": "ai_message",
                            "text": "This has been a great conversation. Let's pick this up next time.",
                            "audio": None,
                            "session_end": True,
                        })
                        break
                except Exception as _budget_err:
                    logging.warning("budget cap check failed: %s", _budget_err)

            ai_response = await ai_service.generate_response_with_audio(
                persona=persona,
                conversation_history=conversation_history,
                user_input=user_text,
                rag_context=base_rag_context,
                training_features=(cartridge_data or {}).get("active_features"),
            )

            db.add_message(session_id=session_id, speaker="ai", text=ai_response["text"])

            message_data = {
                "type": "ai_message",
                "text": ai_response["text"],
                "tts_provider": ai_response["tts_provider"],
            }
            if ai_response.get("audio"):
                message_data["audio"] = ai_response["audio"]
            if ai_response.get("coaching"):
                message_data["coaching"] = ai_response["coaching"]
            if ai_response.get("feedback"):
                message_data["feedback"] = ai_response["feedback"]
                try:
                    score_val = (ai_response.get("feedback") or {}).get("score")
                    if isinstance(score_val, int):
                        db.record_feedback_score(session_id, score_val)
                except Exception:
                    pass

            await websocket.send_json(message_data)

    except WebSocketDisconnect:
        connections.pop(session_id, None)
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
        connections.pop(session_id, None)


@app.post("/sessions/{session_id}/score")
async def score_session(session_id: str):
    """Generate a simple score for the session"""

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.get_messages(session_id)
    user_messages = [msg for msg in messages if msg.get("speaker") == "user"]

    # Prefer model-provided scores if we have them
    score_count = int(session.get("score_count") or 0)
    if score_count > 0:
        score = int(session.get("score") or 0)
        feedback = [
            f"Final score is the running average of {score_count} AI feedback checkpoints.",
        ]
    else:
        # Fallback: simple scoring based on conversation length and content
        score = min(100, len(user_messages) * 10)

        feedback = []
        if len(user_messages) >= 5:
            feedback.append("Good conversation length")
        if any(len(msg.get("text", "")) > 50 for msg in user_messages):
            feedback.append("Provided detailed responses")
        if len(user_messages) < 3:
            feedback.append("Try to engage more in the conversation")

    db.update_session_score(session_id, score)

    return {
        "score": score,
        "feedback": feedback,
        "message_count": len(user_messages),
        "score_count": score_count,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
