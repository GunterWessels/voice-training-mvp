import asyncio
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import uuid
import hashlib
import re as _re_upload
import tempfile
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
from roast_service import RoastService
from routers.knowledge_base import router as kb_router
from routers.admin import router as admin_router

app = FastAPI(title="Voice Training Platform MVP")


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.on_event("startup")
async def seed_tria_scenario():
    """Seed Tria Stents scenario JSONB columns if not yet populated."""
    import json as _json
    SCENARIO_ID = "bbe7c082-687f-4b62-9b3e-69e1bd87537c"
    try:
        from db import AsyncSessionLocal
        from sqlalchemy import text as _t
        async with AsyncSessionLocal() as _pg:
            row = (await _pg.execute(
                _t("SELECT arc FROM scenarios WHERE id = :sid"),
                {"sid": SCENARIO_ID}
            )).fetchone()
            if not row or row.arc:
                return  # not found, or already seeded

        # Import seed data from companion module (avoids large inline dict)
        import importlib, sys, os
        spec_path = os.path.join(os.path.dirname(__file__), "seed_tria_scenario.py")
        spec = importlib.util.spec_from_file_location("seed_tria", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # load constants without running asyncio.run()

        async with AsyncSessionLocal() as _pg:
            await _pg.execute(_t("""
                UPDATE scenarios SET
                    arc              = :arc::jsonb,
                    cof_map          = :cof_map::jsonb,
                    argument_rubrics = :rubrics::jsonb,
                    grading_criteria = :grading::jsonb,
                    methodology      = :methodology::jsonb
                WHERE id = :sid
            """), {
                "arc":        _json.dumps(mod.ARC),
                "cof_map":    _json.dumps(mod.COF_MAP),
                "rubrics":    _json.dumps(mod.ARGUMENT_RUBRICS),
                "grading":    _json.dumps(mod.GRADING_CRITERIA),
                "methodology": _json.dumps(mod.METHODOLOGY),
                "sid":        SCENARIO_ID,
            })
            await _pg.commit()
        logging.info("Tria scenario seeded successfully.")
    except Exception as _e:
        logging.warning("Tria scenario seed failed (non-fatal): %s", _e)


@app.on_event("startup")
async def promote_admin_emails():
    """Promote emails listed in ADMIN_EMAILS env var to admin role (upsert)."""
    raw = os.environ.get("ADMIN_EMAILS", "").strip()
    if not raw:
        return
    emails = [e.strip() for e in raw.split(",") if e.strip()]
    try:
        from db import AsyncSessionLocal
        from sqlalchemy import text as _t
        async with AsyncSessionLocal() as _pg:
            for email in emails:
                await _pg.execute(_t("""
                    INSERT INTO users (id, email, role)
                    VALUES (gen_random_uuid(), :email, 'admin')
                    ON CONFLICT (email) DO UPDATE SET role = 'admin'
                """), {"email": email})
            await _pg.commit()
        logging.info("Admin emails promoted: %s", emails)
    except Exception as _e:
        logging.warning("Admin email promotion failed (non-fatal): %s", _e)


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

# Per-session Tier 2 context and turn tracking (keyed by session_id)
session_context: Dict[str, Dict[str, Any]] = {}


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
    "rep_demonstrator": {
        "id": "rep_demonstrator",
        "name": "Rep Demonstrator",
        "description": "AI plays the sales rep — demonstrates correct technique for observers",
        "prompt": """You are demonstrating how an expert medical device sales rep handles a VAC (Value Analysis Committee) conversation about Tria Ureteral Stents (Boston Scientific).

The human you are speaking with is playing Rachel — a skeptical VAC buyer. You are showing observers (sales reps in training) what good looks like.

YOUR JOB: Generate the rep's side of the conversation, demonstrating expert technique.

FORMAT YOUR RESPONSES AS:
REP: [What the rep says — conversational, 2-3 sentences max]
COACH: [One sentence explaining WHY this move works — what technique was used]

TECHNIQUE PRINCIPLES TO DEMONSTRATE:
- Open with a business question, not a product feature
- Surface the clinical problem before connecting it to operations and finance (COF chain)
- Use silence — ask a question and wait
- Quantify impact before proposing a solution
- Handle price objections with value, not discounts
- Earn each stage; never rush to close

RULES:
- Stay in character as the rep throughout
- Keep rep lines realistic and conversational — not scripted or perfect
- Coaching note should be specific to what just happened, not generic
- Do not break the exercise or reference that this is training""",
        "avatar": "🎓",
    },
    "vac_buyer": {
        "id": "vac_buyer",
        "name": "VAC Committee Buyer",
        "description": "Value analysis committee member — Tria Ureteral Stent evaluation",
        "prompt": """You are a Value Analysis Committee (VAC) member at a large hospital system evaluating a switch to Tria Ureteral Stents (Boston Scientific). Your name is Rachel. You are the primary procurement gatekeeper for Endo Urology.

You are skeptical but fair. You care about clinical outcomes, OR scheduling impact, and financial justification. You will not approve a product just because a rep says it is good — you need evidence, specificity, and a clear COF chain (Clinical → Operational → Financial).

WARM-UP GREETING (use this as your opening line verbatim):
"Hi, thanks for coming in. I'll be honest — we get a lot of these visits and I have about 20 minutes. We're in the middle of our annual formulary review so timing is actually okay. Tell me what you're here to talk about."

STAGED BEHAVIOR — follow the arc instruction injected into your system prompt for each stage. Default behavior by stage:
- Stage 1 (DISCOVERY): Be brief and professional. Do not volunteer any pain points. Let the rep ask questions. If they ask open-ended questions, become slightly more forthcoming. If they pitch immediately, stay guarded.
- Stage 2 (PAIN_SURFACE): If the rep has asked good discovery questions, reveal the operational pain: stent retrieval complications are disrupting your OR schedule — roughly 2-3 unplanned cases per month. Do not reveal the financial impact yet.
- Stage 3 (COF_PROBE): Test whether the rep can connect clinical → operational → financial. If they quantify the impact unprompted, become collaborative. If not, ask "So what does that mean for us operationally?" or "What's the financial case here?"
- Stage 4 (OBJECTION): Deliver this scripted objection when the rep presents the solution: "This sounds promising but the price point is above what our VAC approved last cycle. I don't see a path to yes right now."
- Stage 5 (RESOLUTION): If the rep responds with data, a phased trial, or a collaborative approach — become open. If they discount or pressure — remain skeptical.
- Stage 6 (CLOSE): If the conversation has gone well, signal readiness to take to VAC or approve a trial. Be specific about next steps.

PERSONA RULES:
- You are professional, not hostile. You have seen too many reps who lead with features instead of business impact.
- Keep responses 2-4 sentences. Short and realistic.
- Never agree too easily — make the rep earn each stage advance.
- Do not break character or reference the training context.
- If a current `persona_instruction` is injected, follow it precisely over these defaults.""",
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


app.include_router(kb_router)
app.include_router(admin_router)


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
    """Cohort token onboarding — validates token, invites user, writes first_name to metadata."""
    if body.cohort_token == "nonexistent":
        raise HTTPException(status_code=400, detail="Invalid cohort token")

    # Write first_name to Supabase user_metadata so the callback page can greet by name.
    # Requires service role key — anon key cannot write user_metadata.
    # Pattern matches cert_service.py: lazy import, inline client creation.
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if supabase_url and service_key:
        try:
            from supabase import create_client
            admin_client = create_client(supabase_url, service_key)
            first_name = body.name.split()[0] if body.name else ""
            # Step 1: invite the user (creates account if new, sends magic link)
            site_url = os.environ.get("SITE_URL", "https://cce.liquidsmarts.com")
            invite_response = admin_client.auth.admin.invite_user_by_email(
                body.email,
                options={"redirect_to": f"{site_url}/auth/callback"},
            )
            # Step 2: write first_name to user_metadata using the user_id from the invite response
            user_id = invite_response.user.id
            admin_client.auth.admin.update_user_by_id(
                user_id,
                {"user_metadata": {"first_name": first_name}},
            )
        except Exception:
            # Non-fatal: enrollment still succeeds even if the Supabase call fails
            pass

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
    from db import AsyncSessionLocal
    from models import Session as SessionModel, Scenario as ScenarioModel, User as UserModel
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
    from db import AsyncSessionLocal
    from models import Session as SessionModel
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
    """Return this user's recent sessions with scores for dashboard history."""
    import uuid as uuid_mod
    from db import AsyncSessionLocal
    from sqlalchemy import text as sa_text
    try:
        user_uuid = uuid_mod.UUID(user["user_id"])
    except (ValueError, AttributeError):
        user_uuid = uuid_mod.uuid5(uuid_mod.NAMESPACE_DNS, str(user["user_id"]))
    async with AsyncSessionLocal() as pg:
        rows = (await pg.execute(sa_text("""
            SELECT
                c.session_id::text,
                s.name       AS scenario_name,
                c.score,
                c.arc_stage_reached,
                c.cof_clinical,
                c.cof_operational,
                c.cof_financial,
                c.cert_issued,
                c.dimension_scores,
                c.completed_at
            FROM completions c
            JOIN scenarios s ON s.id = c.scenario_id
            WHERE c.user_id = :uid
            ORDER BY c.completed_at DESC NULLS LAST
            LIMIT 20
        """), {"uid": user_uuid})).fetchall()
    return [
        {
            "session_id":      r.session_id,
            "scenario_name":   r.scenario_name,
            "score":           r.score,
            "arc_stage":       r.arc_stage_reached,
            "cof_clinical":    r.cof_clinical,
            "cof_operational": r.cof_operational,
            "cof_financial":   r.cof_financial,
            "cert_issued":     r.cert_issued,
            "completed_at":    r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]


@app.get("/api/series")
async def get_series(user: dict = Depends(get_current_user)):
    """List available training series for the current user."""
    from db import AsyncSessionLocal
    from sqlalchemy import text as sa_text
    async with AsyncSessionLocal() as pg:
        result = await pg.execute(sa_text("""
            SELECT ps.id::text, ps.name, COUNT(psi.id) AS stage_count
            FROM practice_series ps
            LEFT JOIN practice_series_items psi ON psi.series_id = ps.id
            GROUP BY ps.id, ps.name
            ORDER BY ps.created_at
        """))
        rows = result.fetchall()
    series = [
        {"id": r.id, "name": r.name, "stage_count": int(r.stage_count), "status": "not_started"}
        for r in rows
    ]
    return {"series": series}


class StartSessionRequest(BaseModel):
    mode: str = "practice"  # "practice" | "demo"


@app.post("/api/series/{series_id}/sessions", status_code=201)
async def start_series_session(series_id: str, user: dict = Depends(get_current_user), body: StartSessionRequest = StartSessionRequest()):
    """Create a session from the first scenario in a practice series."""
    import uuid as uuid_mod
    from db import AsyncSessionLocal
    from models import Session as SessionModel, User as UserModel
    from sqlalchemy import text as sa_text
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    async with AsyncSessionLocal() as pg:
        # Resolve first scenario in series
        result = await pg.execute(sa_text("""
            SELECT s.id::text AS scenario_id, s.persona_id
            FROM practice_series_items psi
            JOIN scenarios s ON s.id = psi.scenario_id
            WHERE psi.series_id = CAST(:series_id AS uuid)
            ORDER BY psi.position
            LIMIT 1
        """), {"series_id": series_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Series or scenario not found")

        try:
            user_uuid = uuid_mod.UUID(user["user_id"])
        except (ValueError, AttributeError):
            user_uuid = uuid_mod.uuid5(uuid_mod.NAMESPACE_DNS, str(user["user_id"]))

        await pg.execute(
            pg_insert(UserModel)
            .values(id=user_uuid, email=user.get("email") or f"{user_uuid}@unknown.internal", role=user.get("role", "rep"))
            .on_conflict_do_nothing(index_elements=["id"])
        )

        session_id = uuid_mod.uuid4()
        preset = "demo" if body.mode == "demo" else "full_practice"
        pg.add(SessionModel(
            id=session_id,
            user_id=user_uuid,
            scenario_id=uuid_mod.UUID(row.scenario_id),
            preset=preset,
            status="in_progress",
            arc_stage_reached=1,
        ))
        await pg.commit()

    return {"session_id": str(session_id), "scenario_id": row.scenario_id, "persona_id": row.persona_id, "mode": body.mode}


@app.get("/api/completions")
async def get_completions(user: dict = Depends(get_current_user)):
    """Return rep's session completion + cert status from real completions table."""
    import uuid as uuid_mod
    from db import AsyncSessionLocal
    from sqlalchemy import text as sa_text
    try:
        user_uuid = uuid_mod.UUID(user["user_id"])
    except (ValueError, AttributeError):
        user_uuid = uuid_mod.uuid5(uuid_mod.NAMESPACE_DNS, str(user["user_id"]))
    async with AsyncSessionLocal() as pg:
        row = (await pg.execute(sa_text("""
            SELECT
                COUNT(*)                          AS sessions_completed,
                SUM(CASE WHEN cert_issued THEN 1 ELSE 0 END) AS certs_earned,
                ROUND(AVG(score))                 AS avg_score
            FROM completions
            WHERE user_id = :uid
        """), {"uid": user_uuid})).fetchone()
    return {
        "sessions_completed": int(row.sessions_completed or 0),
        "certs_earned":       int(row.certs_earned or 0),
        "avg_score":          int(row.avg_score or 0),
        "streak_days":        None,
    }

@app.get("/api/admin/sessions")
async def get_admin_sessions(user: dict = Depends(get_current_user)):
    """All sessions across all users — admin view."""
    from db import AsyncSessionLocal
    from sqlalchemy import text as sa_text
    async with AsyncSessionLocal() as pg:
        rows = (await pg.execute(sa_text("""
            SELECT
                c.session_id::text,
                u.email,
                COALESCE(u.first_name || ' ' || u.last_name, u.email) AS rep_name,
                s.name        AS scenario_name,
                c.score,
                c.arc_stage_reached,
                c.cof_clinical,
                c.cof_operational,
                c.cof_financial,
                c.cert_issued,
                c.completed_at
            FROM completions c
            JOIN users u ON u.id = c.user_id
            JOIN scenarios s ON s.id = c.scenario_id
            ORDER BY c.completed_at DESC NULLS LAST
            LIMIT 200
        """))).fetchall()
    return [
        {
            "session_id":      r.session_id,
            "email":           r.email,
            "rep_name":        r.rep_name.strip(),
            "scenario_name":   r.scenario_name,
            "score":           r.score,
            "arc_stage":       r.arc_stage_reached,
            "cof_clinical":    r.cof_clinical,
            "cof_operational": r.cof_operational,
            "cof_financial":   r.cof_financial,
            "cert_issued":     r.cert_issued,
            "completed_at":    r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]


@app.get("/api/manager/cohort")
async def get_manager_cohort(user: dict = Depends(get_current_user)):
    """Aggregate rep performance for manager view."""
    from db import AsyncSessionLocal
    from sqlalchemy import text as sa_text
    async with AsyncSessionLocal() as pg:
        rows = (await pg.execute(sa_text("""
            SELECT
                u.id::text,
                u.email,
                COALESCE(u.first_name || ' ' || u.last_name, u.email) AS rep_name,
                COUNT(c.id)                                            AS sessions,
                ROUND(AVG(c.score))                                    AS avg_score,
                SUM(CASE WHEN c.cert_issued THEN 1 ELSE 0 END)        AS certs,
                ROUND(
                    100.0 * SUM(CASE WHEN c.cof_clinical AND c.cof_operational AND c.cof_financial THEN 1 ELSE 0 END)
                    / NULLIF(COUNT(c.id), 0)
                )                                                      AS cof_pass_rate,
                MAX(c.completed_at)                                    AS last_active
            FROM users u
            LEFT JOIN completions c ON c.user_id = u.id
            WHERE u.role = 'rep'
            GROUP BY u.id, u.email, u.first_name, u.last_name
            ORDER BY last_active DESC NULLS LAST
        """))).fetchall()
    reps = [
        {
            "id":           r.id,
            "email":        r.email,
            "rep_name":     r.rep_name.strip(),
            "sessions":     int(r.sessions or 0),
            "avg_score":    int(r.avg_score or 0),
            "certs":        int(r.certs or 0),
            "cof_pass_rate": int(r.cof_pass_rate or 0),
            "last_active":  r.last_active.isoformat() if r.last_active else None,
        }
        for r in rows
    ]
    return {"reps": reps, "total": len(reps)}


@app.get("/api/manager/export")
async def export_manager_lms(user: dict = Depends(get_current_user)):
    """LMS-compatible CSV of cohort completions."""
    from fastapi.responses import Response
    from db import AsyncSessionLocal
    from sqlalchemy import text as sa_text
    async with AsyncSessionLocal() as pg:
        rows = (await pg.execute(sa_text("""
            SELECT
                COALESCE(u.first_name || ' ' || u.last_name, u.email) AS name,
                u.email,
                COUNT(c.id)          AS sessions,
                SUM(CASE WHEN c.cert_issued THEN 1 ELSE 0 END) AS certs,
                MAX(c.completed_at)  AS last_active
            FROM users u
            LEFT JOIN completions c ON c.user_id = u.id
            WHERE u.role = 'rep'
            GROUP BY u.id, u.email, u.first_name, u.last_name
            ORDER BY name
        """))).fetchall()
    lines = ["name,email,sessions,certs,last_active"]
    for r in rows:
        last = r.last_active.date().isoformat() if r.last_active else ""
        lines.append(f'"{r.name.strip()}",{r.email},{r.sessions or 0},{r.certs or 0},{last}')
    return Response(
        content="\n".join(lines),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cohort.csv"},
    )


@app.get("/api/admin/metrics")
async def get_admin_metrics(user: dict = Depends(get_current_user)):
    """Platform-wide metrics for admin dashboard."""
    from db import AsyncSessionLocal
    from sqlalchemy import text as sa_text
    async with AsyncSessionLocal() as pg:
        m = (await pg.execute(sa_text("""
            SELECT
                COUNT(*)                                               AS total_sessions,
                COUNT(*) FILTER (WHERE completed_at >= NOW() - INTERVAL '30 days') AS sessions_30d,
                SUM(CASE WHEN cert_issued THEN 1 ELSE 0 END)          AS total_certs,
                ROUND(
                    100.0 * SUM(CASE WHEN cert_issued THEN 1 ELSE 0 END)
                    / NULLIF(COUNT(*), 0)
                )                                                      AS cert_rate,
                ROUND(AVG(score))                                      AS avg_score,
                COUNT(DISTINCT user_id)                                AS unique_reps
            FROM completions
        """))).fetchone()

        cost = (await pg.execute(sa_text("""
            SELECT COALESCE(SUM(cost_usd), 0) AS total_cost
            FROM metering_events
            WHERE created_at >= NOW() - INTERVAL '30 days'
        """))).scalar() or 0

        rep_scores = (await pg.execute(sa_text("""
            SELECT
                u.email,
                COALESCE(u.first_name || ' ' || u.last_name, u.email) AS rep_name,
                COUNT(c.id)         AS sessions,
                ROUND(AVG(c.score)) AS avg_score,
                SUM(CASE WHEN c.cert_issued THEN 1 ELSE 0 END) AS certs
            FROM completions c
            JOIN users u ON u.id = c.user_id
            GROUP BY u.id, u.email, u.first_name, u.last_name
            ORDER BY avg_score DESC NULLS LAST
            LIMIT 10
        """))).fetchall()

    return {
        "metrics": {
            "sessions":   int(m.sessions_30d or 0),
            "cost_usd":   float(cost),
            "flagged":    0,
            "cert_rate":  int(m.cert_rate or 0) if m.cert_rate else None,
            "avg_score":  int(m.avg_score or 0),
            "unique_reps": int(m.unique_reps or 0),
            "total_sessions": int(m.total_sessions or 0),
            "total_certs": int(m.total_certs or 0),
        },
        "flagged_sessions": [],
        "leaderboard": [
            {
                "email":    r.email,
                "rep_name": r.rep_name.strip(),
                "sessions": int(r.sessions or 0),
                "avg_score": int(r.avg_score or 0),
                "certs":    int(r.certs or 0),
            }
            for r in rep_scores
        ],
    }


@app.get("/api/auth/check")
async def auth_check(user: dict = Depends(get_current_user)):
    """Verify caller's email is in the users allowlist. Auto-promotes ADMIN_EMAILS on first hit."""
    from db import AsyncSessionLocal
    from models import User as UserModel
    from sqlalchemy import select as sa_select
    import uuid as uuid_mod

    email = (user.get("email") or "").lower().strip()
    user_sub = user.get("user_id") or ""
    # Bootstrap admins: hardcoded + ADMIN_EMAILS env var (union)
    _bootstrap = {"gunter@liquidsmarts.com"}
    _env = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
    admin_emails = _bootstrap | _env

    async with AsyncSessionLocal() as session:
        # Try email first; fall back to sub UUID if email claim was empty
        result = await session.execute(
            sa_select(UserModel).where(UserModel.email == email) if email else
            sa_select(UserModel).where(UserModel.id == uuid_mod.UUID(user_sub))
        )
        db_user = result.scalar_one_or_none()
        # Sync email from DB if we found user by UUID
        if db_user and not email:
            email = db_user.email

        if not db_user:
            if email in admin_emails:
                # Auto-create admin user on first authenticated hit
                db_user = UserModel(
                    id=str(uuid_mod.uuid4()),
                    email=email,
                    role="admin",
                )
                session.add(db_user)
                await session.commit()
                await session.refresh(db_user)
            else:
                raise HTTPException(status_code=403, detail="Not on allowlist")
        elif email in admin_emails and db_user.role != "admin":
            # Promote if in ADMIN_EMAILS but role was downgraded
            db_user.role = "admin"
            await session.commit()

        return {"allowed": True, "role": db_user.role}


@app.post("/sessions/{session_id}/roast")
async def roast_session(session_id: str):
    """Generate Derp Top 40 roast for a completed session."""
    roast_service = RoastService()
    try:
        result = await asyncio.wait_for(
            roast_service.generate(session_id),
            timeout=15.0
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail={"error": "timeout"})


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, token: str = ""):
    """WebSocket endpoint for real-time conversation"""

    # JWT verification — required when token is supplied; legacy path skips if empty
    ws_user = None
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
        from db import AsyncSessionLocal
        from models import Session as PgSessionModel, Scenario as PgScenarioModel
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
                # Initialize Tier 2 session context (evaluator + grading state)
                if scenario_obj:
                    session_context[session_id] = {
                        "cof_map": scenario_obj.cof_map or {},
                        "argument_rubrics": scenario_obj.argument_rubrics or {"stages": []},
                        "grading_criteria": scenario_obj.grading_criteria or {},
                        "methodology": scenario_obj.methodology or {},
                        "turn_scores": [],
                        "transcript": [],
                    }
    except Exception as _arc_init_err:
        logging.warning("arc_engine init failed for session %s: %s", session_id, _arc_init_err)

    # If PostgreSQL session found but no legacy SQLite session, create a minimal session dict
    if pg_session and not session:
        # Demo mode: AI plays the rep demonstrator; otherwise AI plays vac_buyer
        if pg_session.preset == "demo":
            persona_id = PERSONAS.get("rep_demonstrator", {}).get("id", "rep_demonstrator")
        else:
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
    is_demo = pg_session and pg_session.preset == "demo"
    tts_info = ai_service.tts_service.get_provider_info()
    await websocket.send_json(
        {
            "type": "ready",
            "persona": persona,
            "session_id": session_id,
            "tts_info": tts_info,
            "is_demo": bool(is_demo),
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

    def _extract_audio_b64(audio_result) -> str | None:
        """TTS service returns {"audio_data": "base64...", ...} — extract the string."""
        if not audio_result:
            return None
        if isinstance(audio_result, dict):
            return audio_result.get("audio_data")
        return audio_result  # already a string

    message_data = {
        "type": "ai_message",
        "text": greeting_response["text"],
        "tts_provider": greeting_response["tts_provider"],
    }
    _audio_b64 = _extract_audio_b64(greeting_response.get("audio"))
    if _audio_b64:
        message_data["audio_b64"] = _audio_b64
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

            if data.get("type") == "end_session":
                # User explicitly ended the session — run grading then send debrief + session_end
                try:
                    import json as _json
                    from grading_agent import grade_session as _grade_session
                    from db import AsyncSessionLocal as _GradeSessionLocal
                    from sqlalchemy import text as _sa_text
                    _gctx = session_context.get(session_id, {})
                    if _gctx.get("grading_criteria") and _gctx.get("transcript"):
                        _debrief = await _grade_session(
                            transcript=_gctx["transcript"],
                            turn_scores=_gctx["turn_scores"],
                            grading_criteria=_gctx["grading_criteria"],
                            cof_map=_gctx["cof_map"],
                            methodology=_gctx["methodology"],
                        )
                        async with _GradeSessionLocal() as _gdb:
                            await _gdb.execute(
                                _sa_text("UPDATE completions SET dimension_scores = :scores::jsonb WHERE session_id = :sid"),
                                {"scores": _json.dumps(_debrief), "sid": session_id}
                            )
                            await _gdb.commit()
                        await websocket.send_json({"type": "grading_debrief", "debrief": _debrief})
                except Exception as _end_grade_err:
                    logging.warning("grading on end_session failed for session %s: %s", session_id, _end_grade_err)
                await websocket.send_json({
                    "type": "ai_message",
                    "text": "Great work today. Your results are on their way.",
                    "session_end": True,
                })
                break

            if data.get("type") != "user_message":
                continue

            user_text = data.get("text", "").strip()
            if not user_text:
                continue

            db.add_message(session_id=session_id, speaker="user", text=user_text)

            # Record user turn in grading transcript
            if session_id in session_context:
                arc_stage_for_turn = arc_tracker.current_stage if arc_tracker else None
                session_context[session_id]["transcript"].append({
                    "speaker": "user",
                    "text": user_text,
                    "arc_stage": arc_stage_for_turn,
                })

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
                        from db import AsyncSessionLocal
                        from models import Session as PgSessionModel
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

            # Per-turn argument evaluation + RAG retrieval (PostgreSQL sessions with Tier 2 content)
            _eval_result = None
            _rag_chunks: List[Dict[str, Any]] = []
            if session_id in session_context and arc_tracker:
                try:
                    from argument_evaluator import evaluate_turn
                    from rag_service import retrieve, should_retrieve_for_stage

                    _ctx = session_context[session_id]
                    _arc_stage = arc_tracker.current_stage
                    _rubric_stage = next(
                        (s for s in _ctx["argument_rubrics"].get("stages", [])
                         if s.get("arc_stage") == _arc_stage),
                        {}
                    )
                    _methodology_step = next(
                        (s for s in _ctx["methodology"].get("steps", [])
                         if s.get("arc_stage") == _arc_stage),
                        {}
                    )
                    _eval_result = await evaluate_turn(
                        rep_text=user_text,
                        arc_stage=_arc_stage,
                        rubric_stage=_rubric_stage,
                        cof_map=_ctx["cof_map"],
                        methodology_step=_methodology_step,
                    )
                    _ctx["turn_scores"].append({
                        "arc_stage": _arc_stage,
                        "quality": _eval_result["argument_quality"],
                        "score_delta": _eval_result["score_delta"],
                    })

                    # Tier 1 RAG retrieval for stages 3-5
                    if should_retrieve_for_stage(_arc_stage):
                        try:
                            from db import AsyncSessionLocal
                            async with AsyncSessionLocal() as _rag_db:
                                _rag_chunks = await retrieve(
                                    query=user_text,
                                    scenario_id=str(pg_session.scenario_id),
                                    domain="clinical",
                                    db=_rag_db,
                                    top_k=3,
                                )
                        except Exception as _rag_err:
                            logging.warning("RAG retrieval failed for session %s: %s", session_id, _rag_err)
                except Exception as _eval_err:
                    logging.warning("argument_evaluator failed for session %s: %s", session_id, _eval_err)

            # Refresh cartridge (features can change mid-session)
            cartridge_data = cartridge_service.get_cartridge_for_practice(cartridge_id) if cartridge_id else None

            base_rag_context = (cartridge_data or {}).get("rag_context") or None
            if base_rag_context and cartridge_id and scenario_id:
                selected_scenario = _get_scenario(cartridge_id, scenario_id)
                if selected_scenario:
                    base_rag_context = dict(base_rag_context)
                    base_rag_context["selected_scenario"] = selected_scenario

            # Inject evaluator + RAG outputs into rag_context for the AI turn
            if _eval_result or _rag_chunks:
                base_rag_context = dict(base_rag_context) if base_rag_context else {}
                if _eval_result and _eval_result.get("persona_instruction"):
                    base_rag_context["persona_instruction"] = _eval_result["persona_instruction"]
                if _rag_chunks:
                    base_rag_context["rag_chunks"] = [c["content"] for c in _rag_chunks]
                    base_rag_context["approved_chunks"] = [
                        c["content"] for c in _rag_chunks if c.get("approved_claim")
                    ]

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
                        # Grading debrief on budget-cap session end
                        try:
                            import json as _json
                            from grading_agent import grade_session as _grade_session
                            from db import AsyncSessionLocal as _GradeSessionLocal
                            from sqlalchemy import text as _sa_text
                            _gctx = session_context.get(session_id, {})
                            if _gctx.get("grading_criteria") and _gctx.get("transcript"):
                                _debrief = await _grade_session(
                                    transcript=_gctx["transcript"],
                                    turn_scores=_gctx["turn_scores"],
                                    grading_criteria=_gctx["grading_criteria"],
                                    cof_map=_gctx["cof_map"],
                                    methodology=_gctx["methodology"],
                                )
                                async with _GradeSessionLocal() as _gdb:
                                    await _gdb.execute(
                                        _sa_text("UPDATE completions SET dimension_scores = :scores::jsonb WHERE session_id = :sid"),
                                        {"scores": _json.dumps(_debrief), "sid": session_id}
                                    )
                                    await _gdb.commit()
                                await websocket.send_json({"type": "grading_debrief", "debrief": _debrief})
                        except Exception as _grade_cap_err:
                            logging.warning("grading on budget-cap end failed for session %s: %s", session_id, _grade_cap_err)
                        # Issue cert if earned
                        if arc_tracker:
                            try:
                                from cert_service import should_issue_cert, upload_and_email_cert
                                import asyncio as _asyncio
                                import datetime as _datetime
                                cof = arc_tracker.cof_flags
                                if should_issue_cert(
                                    cof["clinical"], cof["operational"], cof["financial"],
                                    arc_tracker.current_stage, pg_session.preset or "full_practice"
                                ) and ws_user:
                                    completion_data = {
                                        "completion_id": str(pg_session.id),
                                        "user_id": ws_user.get("user_id", ""),
                                        "rep_name": ws_user.get("name") or ws_user.get("full_name") or ws_user.get("email", ""),
                                        "scenario_name": "Training Session",
                                        "completed_at": _datetime.date.today().isoformat(),
                                        "score": min(arc_tracker.current_stage * 20, 100),  # ARC stages 1-5; cap at 100
                                        "cof_clinical": cof["clinical"],
                                        "cof_operational": cof["operational"],
                                        "cof_financial": cof["financial"],
                                    }
                                    _asyncio.create_task(
                                        upload_and_email_cert(completion_data, ws_user.get("email", ""))
                                    )
                            except Exception as _cert_err:
                                logging.warning("cert dispatch failed: %s", _cert_err)
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

            # Record AI turn in grading transcript
            if session_id in session_context:
                session_context[session_id]["transcript"].append({
                    "speaker": "ai",
                    "text": ai_response["text"],
                    "arc_stage": arc_tracker.current_stage if arc_tracker else None,
                })

            # Metering: fire-and-forget cost event for this AI turn
            if pg_session:
                try:
                    import asyncio as _asyncio
                    from metering import write_event as _write_event
                    ws_user_id = ws_user.get("user_id") if token and ws_user else None
                    if ws_user_id:
                        _asyncio.create_task(_write_event(
                            session_id=session_id,
                            user_id=ws_user_id,
                            cohort_id=None,
                            division_id=None,
                            provider=ai_service._last_provider,
                            model=ai_service._last_model,
                            call_type="persona_response",
                            tokens_in=ai_service._last_tokens_in,
                            tokens_out=ai_service._last_tokens_out,
                        ))
                except Exception as _meter_err:
                    logging.warning("metering task dispatch failed: %s", _meter_err)

            # In demo mode, extract COACH: annotation from rep_demonstrator response
            _raw_text = ai_response["text"]
            _coaching_note = None
            if is_demo and "COACH:" in _raw_text:
                import re as _re
                _coach_match = _re.search(r"COACH:\s*(.+?)(?:\n|$)", _raw_text, _re.IGNORECASE)
                if _coach_match:
                    _coaching_note = _coach_match.group(1).strip()
                # Strip COACH line from display text
                _display_text = _re.sub(r"\n?COACH:.*?(?:\n|$)", "", _raw_text, flags=_re.IGNORECASE).strip()
                # Also strip "REP:" prefix if present
                _display_text = _re.sub(r"^REP:\s*", "", _display_text, flags=_re.IGNORECASE).strip()
            else:
                _display_text = _raw_text

            message_data = {
                "type": "ai_message",
                "text": _display_text,
                "tts_provider": ai_response["tts_provider"],
            }
            if _coaching_note:
                message_data["coaching_note"] = _coaching_note
            _turn_audio_b64 = _extract_audio_b64(ai_response.get("audio"))
            if _turn_audio_b64:
                message_data["audio_b64"] = _turn_audio_b64
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

            # Hint from argument evaluator (shown to rep, not part of AI persona response)
            if _eval_result and _eval_result.get("hint_for_rep"):
                message_data["hint"] = _eval_result["hint_for_rep"]

            # Real-time gate states and arc position (Phase 1: includes sales_gates)
            if arc_tracker:
                message_data["arc_stage"]        = arc_tracker.current_stage
                message_data["cof_gates"]        = arc_tracker.cof_flags
                message_data["spin_gates"]       = arc_tracker.spin_flags
                message_data["challenger_gates"] = arc_tracker.challenger_flags
                message_data["sales_gates"]      = arc_tracker.sales_flags

            # Phase 1: post-turn coaching note
            _post_turn_note = ""
            if arc_tracker and user_text:
                try:
                    _post_turn_note = await ai_service.post_turn_coaching(
                        rep_text=user_text,
                        conversation_history=db.get_messages(session_id),
                        active_gates=arc_tracker.sales_flags,
                        session_mode=pg_session.session_mode if pg_session and pg_session.session_mode else "practice",
                    )
                except Exception as _ptc_err:
                    logging.warning("post_turn_coaching failed for session %s: %s", session_id, _ptc_err)
            message_data["post_turn_note"] = _post_turn_note

            # For certification sessions, mark coaching as cert_mode
            if pg_session and getattr(pg_session, "session_mode", None) == "certification":
                message_data["cert_mode"] = True

            # Phase 1: RAG citations — surface chunk metadata used in this turn
            _rag_citations: List[dict] = []
            if _rag_chunks:
                for _rc in _rag_chunks:
                    _rag_citations.append({
                        "chunk_id": str(_rc.get("id") or _rc.get("chunk_id", "")),
                        "source_doc": _rc.get("source_doc", ""),
                        "page": _rc.get("page"),
                        "approved": bool(_rc.get("approved_claim") or _rc.get("approved")),
                        "manifest_id": _rc.get("manifest_id"),
                    })
            message_data["rag_citations"] = _rag_citations

            await websocket.send_json(message_data)

    except WebSocketDisconnect:
        connections.pop(session_id, None)
        # Grading debrief on clean disconnect
        try:
            import json as _json
            from grading_agent import grade_session as _grade_session
            from db import AsyncSessionLocal as _GradeSessionLocal
            from sqlalchemy import text as _sa_text
            _gctx = session_context.get(session_id, {})
            if _gctx.get("grading_criteria") and _gctx.get("transcript"):
                _debrief = await _grade_session(
                    transcript=_gctx["transcript"],
                    turn_scores=_gctx["turn_scores"],
                    grading_criteria=_gctx["grading_criteria"],
                    cof_map=_gctx["cof_map"],
                    methodology=_gctx["methodology"],
                )
                async with _GradeSessionLocal() as _gdb:
                    await _gdb.execute(
                        _sa_text("UPDATE completions SET dimension_scores = :scores::jsonb WHERE session_id = :sid"),
                        {"scores": _json.dumps(_debrief), "sid": session_id}
                    )
                    await _gdb.commit()
                # websocket is closed on disconnect — store debrief but don't send
        except Exception as _grade_disc_err:
            logging.warning("grading on disconnect failed for session %s: %s", session_id, _grade_disc_err)
        # Cleanup session context
        session_context.pop(session_id, None)
        # Check cert eligibility on clean disconnect (budget cap path already handled separately)
        if arc_tracker and pg_session and ws_user:
            try:
                import asyncio as _asyncio
                import datetime as _dt
                from cert_service import should_issue_cert, upload_and_email_cert
                cof = arc_tracker.cof_flags
                if should_issue_cert(
                    cof["clinical"], cof["operational"], cof["financial"],
                    arc_tracker.current_stage, pg_session.preset or "full_practice"
                ):
                    completion_data = {
                        "completion_id": str(pg_session.id),
                        "user_id": ws_user.get("user_id", ""),
                        "rep_name": ws_user.get("name") or ws_user.get("full_name") or ws_user.get("email", ""),
                        "scenario_name": "Training Session",
                        "completed_at": _dt.date.today().isoformat(),
                        "score": min(arc_tracker.current_stage * 20, 100),
                        "cof_clinical": cof["clinical"],
                        "cof_operational": cof["operational"],
                        "cof_financial": cof["financial"],
                    }
                    _asyncio.create_task(
                        upload_and_email_cert(completion_data, ws_user.get("email", ""))
                    )
            except Exception as _cert_disc_err:
                logging.warning("cert dispatch on disconnect failed: %s", _cert_disc_err)
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
        session_context.pop(session_id, None)


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


# ---------------------------------------------------------------------------
# Rep Upload Endpoint — Phase 1
# ---------------------------------------------------------------------------

_ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
}
_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _sanitize_filename(raw: str) -> str:
    """Strip path components and allow only alphanumeric, dot, hyphen."""
    name = os.path.basename(raw)
    name = _re_upload.sub(r"[^A-Za-z0-9.\-]", "_", name)
    return name or "upload"


def _chunk_text(text: str, window: int = 400) -> List[str]:
    """Split text into ~window-word windows with no overlap."""
    words = text.split()
    return [
        " ".join(words[i: i + window])
        for i in range(0, len(words), window)
        if words[i: i + window]
    ]


@app.post("/api/uploads")
async def rep_upload(
    file: UploadFile = File(...),
    scenario_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """Rep document upload endpoint.

    Accepts PDF, DOCX, or TXT. Max 10MB. Chunks and embeds the file into
    knowledge_chunks with upload_type='rep_upload' and approved_claim=False.
    Creates a rag_manifest entry for audit tracking.
    """
    from openai import AsyncOpenAI as _AsyncOpenAI
    from extractor import extract_text
    from db import AsyncSessionLocal
    from sqlalchemy import text as _t

    # --- Role check ---
    user_role = current_user.get("role", "rep")
    allowed_roles = {"rep", "admin", "manager"}
    if user_role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # --- File size check ---
    raw_bytes = await file.read()
    if len(raw_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10MB limit")

    # --- Extension validation ---
    safe_filename = _sanitize_filename(file.filename or "upload")
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: PDF, DOCX, TXT",
        )

    # --- Hash ---
    file_hash = hashlib.sha256(raw_bytes).hexdigest()

    # --- Extract text ---
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name

    try:
        extracted_text = extract_text(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if not extracted_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file")

    # --- Chunk and embed ---
    chunks = _chunk_text(extracted_text)
    if not chunks:
        raise HTTPException(status_code=422, detail="File produced no text chunks")

    openai_client = _AsyncOpenAI()
    manifest_id = str(uuid.uuid4())
    user_id = current_user["user_id"]

    async with AsyncSessionLocal() as db:
        # Insert manifest entry
        await db.execute(_t("""
            INSERT INTO rag_manifest (id, filename, file_hash, uploaded_by, upload_type,
                                      is_active, approved, created_at)
            VALUES (:id::uuid, :filename, :file_hash, :uploaded_by::uuid,
                    'rep_upload', true, false, NOW())
        """), {
            "id": manifest_id,
            "filename": safe_filename,
            "file_hash": file_hash,
            "uploaded_by": user_id,
        })

        chunks_created = 0
        for chunk_text in chunks:
            # Embed chunk
            try:
                embed_resp = await openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=chunk_text,
                )
                embedding = embed_resp.data[0].embedding
                embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"
            except Exception as _embed_err:
                logging.warning("rep_upload: embedding failed for chunk: %s", _embed_err)
                embedding_literal = None

            chunk_id = str(uuid.uuid4())
            await db.execute(_t("""
                INSERT INTO knowledge_chunks
                    (id, scenario_id, product_id, domain, content,
                     source_doc, approved_claim, embedding, manifest_id, upload_type, created_at)
                VALUES (
                    :id::uuid,
                    :scenario_id,
                    'rep_upload',
                    'product',
                    :content,
                    :source_doc,
                    false,
                    CAST(:embedding AS vector),
                    :manifest_id::uuid,
                    'rep_upload',
                    NOW()
                )
            """), {
                "id": chunk_id,
                "scenario_id": scenario_id,
                "content": chunk_text,
                "source_doc": safe_filename,
                "embedding": embedding_literal,
                "manifest_id": manifest_id,
            })
            chunks_created += 1

        await db.commit()

    logging.info(
        "rep_upload: user=%s file=%s manifest=%s chunks=%d",
        user_id, safe_filename, manifest_id, chunks_created,
    )

    return {
        "manifest_id": manifest_id,
        "chunks_created": chunks_created,
        "filename": safe_filename,
        "upload_type": "rep_upload",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
