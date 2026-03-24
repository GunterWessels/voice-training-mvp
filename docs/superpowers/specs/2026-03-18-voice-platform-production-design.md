# Voice Training Platform — Production Design Spec
**Version:** 1.1
**Date:** 2026-03-18
**Author:** LiquidSMARTS™
**Status:** Approved for Implementation

---

## 1. Executive Summary

The LiquidSMARTS™ Voice Training Platform is an AI-powered sales certification tool for MedTech sales professionals. This document specifies the production-grade rebuild of the existing MVP for deployment to Boston Scientific (BSCI) across multiple commercial divisions, starting with Endo Urology (Tria Stents) and Cardiac Rhythm Management.

Rep input is captured via the browser's Web Speech API (client-side speech-to-text). The resulting text is what the AI responds to. This is not server-side transcription. Supported browsers: Chrome/Edge (full), Safari (good), Firefox (limited — voice input degrades to text field).

The platform delivers:
- Live voice conversations with AI buyer personas following choreographed conversation arcs
- COF Framework evaluation (Clinical, Operational, Financial) with objective gate tracking
- LiquidSMARTS-issued CE completion certificates and BSCI LMS-compatible exports
- Three-tier utilization metering: LiquidSMARTS ops, BSCI manager reporting, API cost tracking
- Mobile-first UX with practice series, agent presets, and easter egg celebrations

**Deployment target:** Railway (cloud, public URL)
**Auth:** Supabase magic links + cohort tokens. SSO deferred.
**Stack:** FastAPI (Python) backend + Next.js 15 (TypeScript) frontend + Railway PostgreSQL

---

## 2. Problem Statement

The existing MVP demonstrates the core value proposition — AI voice conversations with buyer personas — but cannot be deployed to a client in its current state:

| Gap | Impact |
|-----|--------|
| No authentication | Any user can access all sessions and burn API quota |
| CORS locked to localhost | Platform breaks on any deployed URL |
| SQLite with no WAL mode | Concurrent writes corrupt the database |
| Errors exposed to client | Internal stack traces leak through WebSocket |
| No rate limiting | Single user can exhaust monthly API budget in minutes |
| React (CRA) frontend | 28 known build-tool CVEs; not TypeScript; not portal-aligned |
| No metering | Cannot track usage, cost, or completion at client level |
| Generic personas | No BSCI product context, no scripted conversation arc |
| Length-based scoring | Does not measure COF mastery — measures wordcount |
| No CE/cert system | No completion artifact for reps or LMS |

---

## 3. Goals and Success Metrics

### Goals
1. Deploy a production-ready platform that BSCI reps can access from their phones with a single link
2. Deliver measurable COF skill improvement through choreographed, product-specific scenarios
3. Issue completion certificates and LMS-compatible exports for BSCI training records
4. Meter API utilization with enough granularity to price the service and monitor cost

### Success Metrics
| Metric | Target |
|--------|--------|
| Time from link to first conversation | < 60 seconds |
| Mobile usability (iOS Safari, Android Chrome) | Zero layout failures |
| COF gate accuracy vs. human reviewer | > 90% agreement |
| API cost per completed session | < $0.40 average |
| Platform uptime | > 99.5% monthly |
| First-session completion rate | > 70% |
| Cert issuance rate (reps who complete 3+ sessions) | > 80% |

---

## 4. Architecture

### 4.1 Topology

```
BSCI Rep (mobile browser)
    ↕ HTTPS / WSS (Railway TLS)
Next.js 15 TypeScript (Railway)
  - Auth pages (magic link, cohort token)
  - Rep dashboard (queue, history, certs)
  - Manager dashboard (cohort view, transcripts, LMS export)
  - Admin dashboard (ops metrics, cost, flagged sessions)
  - Handoff links (QR + shareable URL per scenario)
    ↕ Internal API (same Railway service)
FastAPI (Python, Railway)
  - WebSocket conversation engine
  - AI service (OpenAI GPT-4o-mini / Claude Haiku)
  - TTS service (ElevenLabs / OpenAI TTS)
  - Filler audio cache
  - Metering event writer
  - Supabase JWT middleware
    ↕
Railway PostgreSQL
  - All persistent data (see Data Model)
Supabase Auth
  - JWT issuance only (no Supabase DB used)
OpenAI API / Anthropic API
ElevenLabs API
```

### 4.2 What Changes vs. Current MVP

| Layer | Current | Production |
|-------|---------|------------|
| Frontend | React 18 (CRA, JS) | Next.js 15 (TypeScript) |
| Database | SQLite (2 files) | Railway PostgreSQL |
| Auth | None | Supabase JWT middleware |
| Deployment | local `start.sh` | Docker + Railway CI/CD |
| Metering | None | `metering_events` table, cost rollups |
| Scoring | Message count heuristic | COF arc-stage tracker |

### 4.3 What Stays

`ai_service.py`, `tts_service.py`, and `cartridge_service.py` are retained and hardened. The WebSocket conversation engine in `main.py` is retained with security additions. The core AI orchestration logic is not rewritten.

**WebSocket worker constraint:** The FastAPI process runs as a single worker (`--workers 1`). In-memory WebSocket connection state (`connections` dict) is process-local. A second worker would make session routing non-deterministic under Railway's round-robin load balancer. If horizontal scaling is required in a future phase, the `connections` dict must be replaced with a Redis pub/sub session registry before enabling multiple workers.

---

## 5. Data Model (PostgreSQL)

### 5.1 Tables

```sql
-- Users (populated from Supabase Auth)
CREATE TABLE users (
    id UUID PRIMARY KEY,                -- Supabase UID
    email TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    role TEXT NOT NULL DEFAULT 'rep',   -- 'rep' | 'manager' | 'admin'
    cohort_id UUID REFERENCES cohorts(id),
    division_id UUID REFERENCES divisions(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ
);

-- Divisions (BSCI commercial divisions)
CREATE TABLE divisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,                 -- 'Endo Urology', 'Cardiac Rhythm Management'
    slug TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cohorts (training groups within a division)
CREATE TABLE cohorts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    division_id UUID NOT NULL REFERENCES divisions(id),
    manager_id UUID REFERENCES users(id),
    cohort_token TEXT UNIQUE,           -- shared access token for group onboarding
    celebrations_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scenarios (choreographed product scenarios)
CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    division_id UUID NOT NULL REFERENCES divisions(id),
    product_name TEXT,                  -- 'Tria Stents', 'EMBLEM S-ICD', etc.
    persona_id TEXT NOT NULL,           -- maps to persona registry
    arc JSONB NOT NULL,                 -- conversation arc stages (see Section 7)
    celebration_triggers JSONB,         -- easter egg conditions
    cartridge_id TEXT,                  -- links to cartridge_service
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions (one per training conversation)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    scenario_id UUID NOT NULL REFERENCES scenarios(id),
    preset TEXT DEFAULT 'full_practice', -- 'quick_drill' | 'full_practice' | 'cert_run'
    status TEXT DEFAULT 'active',        -- 'active' | 'completed' | 'abandoned'
    arc_stage_reached INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER
);

-- Messages (conversation turns)
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id),
    speaker TEXT NOT NULL,              -- 'user' | 'ai'
    text TEXT NOT NULL,
    arc_stage INTEGER,                  -- stage active when message was sent
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Completions (issued when COF gates pass + arc >= stage 5)
CREATE TABLE completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL UNIQUE REFERENCES sessions(id),
    user_id UUID NOT NULL REFERENCES users(id),
    scenario_id UUID NOT NULL REFERENCES scenarios(id),
    score INTEGER NOT NULL,
    cof_clinical BOOLEAN NOT NULL,
    cof_operational BOOLEAN NOT NULL,
    cof_financial BOOLEAN NOT NULL,
    arc_stage_reached INTEGER NOT NULL,
    cert_issued BOOLEAN DEFAULT FALSE,
    cert_url TEXT,
    lms_export_ready BOOLEAN DEFAULT TRUE,
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Metering Events (one row per API call)
CREATE TABLE metering_events (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id),
    user_id UUID NOT NULL REFERENCES users(id),
    cohort_id UUID REFERENCES cohorts(id),
    division_id UUID REFERENCES divisions(id),
    provider TEXT NOT NULL,             -- 'openai' | 'anthropic' | 'elevenlabs'
    model TEXT,
    call_type TEXT,                     -- 'persona_response' | 'analysis' | 'tts' | 'filler'
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd NUMERIC(10,6),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Practice Series
CREATE TABLE practice_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    assigned_to_cohort_id UUID REFERENCES cohorts(id),
    assigned_to_user_id UUID REFERENCES users(id),
    due_date DATE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Practice Series Items (ordered scenario list — explicit position column)
CREATE TABLE practice_series_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_id UUID NOT NULL REFERENCES practice_series(id) ON DELETE CASCADE,
    scenario_id UUID NOT NULL REFERENCES scenarios(id),
    position INTEGER NOT NULL,          -- 1-based ordering, enforced unique per series
    UNIQUE (series_id, position)
);
```

### 5.2 Metering Event Population

`cohort_id` and `division_id` on `metering_events` are nullable foreign keys resolved by the session handler at write time — not passed by the client. When a metering event is written, the handler looks up `sessions.scenario_id → scenarios.division_id` and `sessions.user_id → users.cohort_id` and populates those columns. This keeps the metering writer free of client-supplied data.

### 5.3 Indexes

```sql
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_scenario_id ON sessions(scenario_id);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_metering_events_session_id ON metering_events(session_id);
CREATE INDEX idx_metering_events_timestamp ON metering_events(timestamp);
CREATE INDEX idx_completions_user_id ON completions(user_id);
```

---

## 6. Auth & Security

### 6.1 Authentication Flow

**Individual reps (magic link):**
1. Admin or manager creates user record and triggers Supabase magic link email
2. Rep clicks link → Supabase issues JWT → stored in httpOnly cookie
3. All FastAPI endpoints verify JWT via `python-jose` middleware
4. All Next.js server components verify JWT via Supabase client

**Group onboarding (cohort token):**
1. Manager shares a URL: `https://train.liquidsmarts.com/join/<cohort_token>`
2. Rep enters name + email → system checks if email already exists in Supabase:
   - **New user:** Supabase creates account → magic link sent → rep assigned to cohort on first login
   - **Existing user, no active session:** Magic link re-sent to their email
   - **Existing user, valid session cookie:** Redirect directly to dashboard (no re-auth needed)
3. Cohort assignment is idempotent — re-visiting the join URL does not change an already-assigned cohort

**Next.js 15 JWT propagation:** Auth uses the `@supabase/ssr` package with a `middleware.ts` that reads the session cookie and refreshes the JWT on every server request. Server components access the session via `createServerClient()`. Client components use `createBrowserClient()`. All WebSocket connections include the JWT as a query parameter (`?token=<jwt>`) verified by FastAPI middleware on connection.

### 6.2 Role-Based Access

| Role | Access |
|------|--------|
| `rep` | Own sessions, own completions, assigned practice series |
| `manager` | Own cohort's reps, sessions, transcripts, LMS export |
| `admin` | All data, cost dashboard, all cohorts |

### 6.3 Security Hardening

- **CORS:** Configurable via `ALLOWED_ORIGINS` env var. Default: Railway production URL only.
- **Rate limiting:** `slowapi` on FastAPI. Limits: 60 requests/min per IP, 10 WebSocket connections/min per user.
- **Error sanitization:** All exceptions caught at WebSocket and REST handlers. Client receives `{"error": "processing_error"}` only. Full error logged server-side.
- **Token budget:** Per-session token cap enforced in `ai_service.py`. Configurable per preset (Quick Drill: 2,000 tokens, Full Practice: 5,000, Cert Run: 8,000). On cap hit, persona wraps gracefully.
- **Input size limit:** WebSocket messages capped at 4,096 bytes. Oversized messages dropped with `{"error": "message_too_long"}`.
- **API keys:** Stored as Railway environment variables. Never logged, never sent to client.

---

## 7. Scenario Choreography

### 7.1 Conversation Arc Structure

Each scenario carries a `arc` JSONB field defining staged progression:

```json
{
  "stages": [
    {
      "id": 1,
      "name": "DISCOVERY",
      "persona_instruction": "Respond briefly and vaguely. Do not volunteer pain points. Wait for the rep to ask at least two open-ended questions before becoming more forthcoming.",
      "unlock_condition": "open_ended_questions >= 2",
      "max_turns": 6
    },
    {
      "id": 2,
      "name": "PAIN_SURFACE",
      "persona_instruction": "Reveal the primary operational pain (stone management throughput). Still withhold financial impact. Respond to direct clinical questions honestly.",
      "unlock_condition": "cof_clinical_mentioned == true",
      "max_turns": 5
    },
    {
      "id": 3,
      "name": "COF_PROBE",
      "persona_instruction": "Test whether the rep connects clinical, operational, and financial domains. If they quantify OR scheduling impact, become collaborative and help them do the math.",
      "unlock_condition": "cof_all_mentioned == true",
      "max_turns": 8
    },
    {
      "id": 4,
      "name": "OBJECTION",
      "persona_instruction": "Introduce the scripted objection exactly: 'This sounds promising but the price point is above what our VAC approved last cycle. I don't see a path to yes right now.'",
      "unlock_condition": "solution_presented == true",
      "max_turns": 4
    },
    {
      "id": 5,
      "name": "RESOLUTION",
      "persona_instruction": "If rep pivots collaboratively (configuration, phased trial, data review), respond positively and move toward commitment. If rep pivots defensively (discounts, pressure), remain skeptical.",
      "unlock_condition": "objection_addressed == true",
      "max_turns": 6
    },
    {
      "id": 6,
      "name": "CLOSE",
      "persona_instruction": "Signal readiness to take to VAC or agree to a trial. Session can end here.",
      "unlock_condition": "resolution_positive == true",
      "max_turns": 3
    }
  ]
}
```

### 7.2 Condition Evaluation Engine

Unlock conditions are evaluated against the accumulated conversation history using a deterministic keyword/pattern matcher — no LLM call required. Each condition maps to a specific detection rule:

| Condition | Detection Rule |
|-----------|---------------|
| `open_ended_questions >= N` | Count user turns containing a question mark where the sentence does not start with "Is", "Are", "Do", "Does", "Did", "Can", "Will", "Would", "Have", "Has" |
| `cof_clinical_mentioned` | User turn contains >= 1 term from the Clinical seed list |
| `cof_operational_mentioned` | User turn contains >= 1 term from the Operational seed list |
| `cof_financial_mentioned` | User turn contains >= 1 term from the Financial seed list |
| `cof_all_mentioned` | All three COF flags are TRUE |
| `solution_presented` | User turn contains >= 1 term from the Solution seed list AND turn length >= 30 words |
| `objection_addressed` | User turn follows an AI turn containing the scripted objection phrase AND does not contain discount/price-cut terms |
| `resolution_positive` | Most recent AI turn contains >= 1 term from the Positive-signal seed list |

**COF Seed Term Lists (minimum viable — extend per scenario):**

```python
COF_SEEDS = {
    "clinical": [
        "patient", "complication", "outcome", "infection", "stent", "fragment",
        "stone", "encrustation", "urinary", "clinical", "care", "safety", "risk"
    ],
    "operational": [
        "OR", "schedule", "throughput", "turnover", "workflow", "procedure",
        "time", "efficiency", "volume", "capacity", "staff", "utilization"
    ],
    "financial": [
        "cost", "budget", "revenue", "reimbursement", "ROI", "savings",
        "expense", "margin", "price", "spend", "financial", "dollar", "investment"
    ],
    "solution": [
        "Tria", "stent", "solution", "product", "system", "platform",
        "offer", "propose", "address", "resolve", "help", "benefit"
    ],
    "positive_signal": [
        "trial", "pilot", "VAC", "committee", "consider", "interested",
        "explore", "next step", "meeting", "approve", "move forward"
    ],
    "discount_defense": [
        "discount", "lower price", "price reduction", "cut", "cheaper", "negotiate down"
    ]
}
```

**Accuracy target:** >= 90% agreement with human reviewer on a 50-sample labeled transcript fixture (see Section 13.1). Seed lists are extended per scenario during content authoring.

### 7.4 Arc Stage Tracker

The FastAPI session handler maintains stage state per session. At each turn:
1. Evaluate unlock condition against conversation history (lightweight keyword + pattern check, not GPT)
2. If condition met, advance stage and update `sessions.arc_stage_reached`
3. Inject new `persona_instruction` into next system prompt
4. Check `celebration_triggers` for any newly met conditions

### 7.5 Initial Scenarios

| Scenario | Division | Product | Persona | Arc Stages |
|----------|----------|---------|---------|-----------|
| VAC Stakeholder — Tria Stents | Endo Urology | Tria Ureteral Stents | VAC/Procurement Buyer (female) | 6 stages above |
| EP Lab Director — S-ICD | Cardiac Rhythm | EMBLEM S-ICD | EP Lab Director (female) | 6 stages adapted for cardiac context |

---

## 8. Conversation UX & Pacing

### 8.1 Filler Audio Cache

Pre-generated at deploy time via a one-time script (`scripts/generate_filler_audio.py`). One set of 10 clips per persona, generated in that persona's ElevenLabs voice, stored under `/public/filler/<persona_id>/`. 30 total clips (3 personas x 10 clips).

```
/public/filler/vac_buyer/hmm.mp3
/public/filler/vac_buyer/go-on.mp3
... (10 clips)
/public/filler/ep_lab_director/hmm.mp3
... (10 clips)
/public/filler/clinical_director/hmm.mp3
... (10 clips)
```

Clip names: `hmm`, `go-on`, `interesting`, `thats-a-lot`, `ok`, `right-right`, `mm-hmm`, `long-answer`, `tell-me-more`, `noted`.

**Trigger logic (client-side):**
- Start timer when rep stops speaking (VAD silence detection)
- If AI response not received within 800ms → play random filler clip
- Track last played clip to prevent immediate repeat
- Cancel filler if AI response arrives before clip ends

### 8.2 First-Load Onboarding Overlay

Shown once per user (stored in localStorage + user profile). Auto-dismisses at 20 seconds.

**Audio script (female voice, warm tone):**
> "Quick heads up — this is a live conversation arc. Your buyer is real enough to push back. She's listening for whether you can surface what's going wrong clinically, operationally, and financially — and move her toward a trial. Discovery first, resolution follows. You've got this. Tap to start."

**Visual:** Clean dark overlay, animated waveform, text synchronized with audio. "Skip" tap target visible from second 3.

### 8.3 In-Session Wayfinding

- **Arc progress strip:** 6 dots at top of screen. Active dot pulses. No labels during session.
- **Post-session arc breakdown:** Dots expand with stage names and turn counts. Stalled stages highlighted.
- **Thinking delay:** 1.5–2.5 second pause before AI audio begins (configurable per preset). Quick Drill: 1s. Cert Run: 2s.

### 8.4 Voice Persona Mapping

| Persona | ElevenLabs Voice | OpenAI Voice | Fallback |
|---------|-----------------|--------------|---------|
| VAC Buyer | Rachel (21m00Tcm4TlvDq8ikWAM) | nova | Browser: en-US female |
| Clinical Director | Domi (AZnzlk1XvdvUeBnXmlld) | alloy | Browser: en-US female |
| EP Lab Director | Bella (EXAVITQu4vr4xnSDxMaL) | shimmer | Browser: en-US female |

All persona voices are female. Voice settings: stability 0.55, similarity_boost 0.6, style 0.1.

---

## 9. Feedback, CE Credit & Completion

### 9.1 End-of-Session Feedback

**Layer 1 — COF Gate Report (immediate):**
Three boolean gates derived from arc stage tracker:
- Clinical gate: `cof_clinical_mentioned` flag set during arc evaluation
- Operational gate: `cof_operational_mentioned` flag
- Financial gate: `cof_financial_mentioned` flag

Each gate displayed as a checkmark (passed) or open circle (missed) with a one-line explanation.

**Layer 2 — Performance Narrative (GPT-generated):**
- Temperature: 0.3 (consistent tone)
- Max tokens: 120
- Prompt: positive-tilt coaching voice, 2–3 sentences, references specific moments from transcript
- Delivered as audio (persona voice) + text simultaneously

### 9.2 CE Completion Certificate

**Issuance conditions:**
- All 3 COF gates passed
- Arc stage reached >= 5 (RESOLUTION)
- Preset is `full_practice` or `cert_run` (Quick Drill sessions are not cert-eligible)

**Certificate contents:**
- Rep name, scenario name, date, score, COF gate breakdown
- LiquidSMARTS™ branding, signed by Dr. Gunter Wessels
- Unique completion ID (UUID, verifiable)

**Delivery:**
- Auto-emailed to rep on issuance
- Available in rep profile for download
- PDF generated server-side via `reportlab` (Python)

#### 9.2.1 Certificate Generation Pipeline

**PDF generation:** `reportlab` renders a single-page PDF using brand assets from `backend/assets/`:
- `ls_logo.png` — LiquidSMARTS™ logo (top left)
- `signature.png` — Dr. Gunter Wessels signature image (bottom)
- Fonts: Oswald (headings), Manrope (body) — loaded from `backend/assets/fonts/`
- Layout: white background, navy header bar, completion ID in footer as small text

**PDF storage:** Generated PDFs stored in Supabase Storage bucket `certificates` (public read, service-role write). Path: `certificates/<user_id>/<completion_id>.pdf`. The public URL is written to `completions.cert_url`.

**Email delivery:** Transactional email via Resend (`resend` Python SDK). API key stored as `RESEND_API_KEY` env var (add to Section 12.1 env var list). From address: `training@liquidsmarts.com`. Template: plain text + PDF attachment.

**Env var addition to Section 12.1:**
```
RESEND_API_KEY
SUPABASE_STORAGE_BUCKET=certificates
```

### 9.3 LMS Export

Each `completions` row is structured for xAPI compatibility:
```json
{
  "actor": {"name": "Rep Name", "mbox": "mailto:rep@bsci.com"},
  "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
  "object": {"id": "https://train.liquidsmarts.com/scenarios/<id>", "definition": {"name": {"en-US": "Tria Stents VAC Scenario"}}},
  "result": {"score": {"scaled": 0.87}, "success": true, "completion": true},
  "timestamp": "2026-03-18T14:30:00Z"
}
```

Manager export: CSV download from manager dashboard. Future: direct xAPI push to BSCI LMS.

### 9.4 Agent Presets

| Preset | Token Budget | Thinking Delay | Feedback Overlay | Cert Eligible | Use Case |
|--------|-------------|----------------|-----------------|---------------|---------|
| Quick Drill | 2,000 | 1.0s | Minimal | No | 5-min phone warmup |
| Full Practice | 5,000 | 1.8s | Full | Yes | Standard session |
| Cert Run | 8,000 | 2.2s | None during | Yes | High-stakes cert attempt |

### 9.5 Practice Series

- Manager creates a named series: ordered list of scenarios, due date
- Assigned to a cohort or individual rep
- Rep home screen shows queue with progress indicator
- Completing a series unlocks a series-completion easter egg

---

## 10. Metering & Dashboards

### 10.1 Cost Model

Per `metering_event` row:
```
openai gpt-4o-mini:  input $0.15/1M tokens, output $0.60/1M tokens
openai tts-1:        $0.015/1K characters
elevenlabs:          $0.18/1K characters (eleven_monolingual_v1)
anthropic haiku:     input $0.25/1M tokens, output $1.25/1M tokens
```

Cost computed at write time and stored in `cost_usd`. Aggregated via SQL GROUP BY.

**Per-session cost guardrail:** If `SUM(cost_usd) WHERE session_id = X` exceeds preset budget cap, FastAPI sends persona wrap-up signal. Session closes cleanly.

### 10.2 Admin Ops Dashboard (Gunter)

- Sessions by day (chart, last 30 days)
- API spend by provider (chart, rolling 30 days)
- Cost per session average by division
- Flagged sessions (cost > 2x average)
- Completion rate by cohort
- Active users last 7 days
- CSV export: full session log

### 10.3 Manager Dashboard (BSCI)

- Rep list: name, sessions completed, last active, cert status, COF pass rate
- Tap rep: session history, arc stage reached per session, score trend
- Tap session: full transcript, arc breakdown, COF gates
- LMS export: CSV of all completions for their cohort
- Practice series: assign, track, see completion

### 10.4 Rep Dashboard

- Practice series queue with scenario cards
- Session history with scores and cert badges
- Streak counter (days with at least one session)
- Certificate collection

---

## 11. Easter Eggs & Celebration Layer

All triggers evaluated client-side after session completion or at real-time milestones. No additional API calls.

| Trigger Condition | Celebration |
|-------------------|-------------|
| `sessions.count == 1` (first ever) | Confetti burst + audio: *"You just had your first AI sales conversation. Most people don't even try."* |
| `completions` first row with all 3 COF gates TRUE | Animated gold COF badge + 3-tone chime |
| `sessions.streak >= 3` | Persona breaks character: *"OK I have to say — you're getting better at this."* |
| Arc stage 5 reached in < 8 minutes | Speed badge: *"Fast hands."* |
| First cert issued | Certificate animates in with ink-drawing effect + signature sound |
| Practice series completed same day as assigned | *"Same-day finish. Noted."* |
| Session after a failed attempt, COF all pass | *"Redemption arc complete."* |

Celebrations stored as `celebration_triggers` JSONB on the scenario. Field contains: `condition` (evaluable expression), `type` (confetti/audio/badge/persona), `content` (text or audio file reference). Cohort-level toggle: `celebrations_enabled BOOLEAN DEFAULT TRUE`.

---

## 12. Deployment

### 12.1 Railway Configuration

```
Services:
  - voice-training-app (Docker, Next.js 15 serves as frontend + API proxy)
  - voice-training-backend (Docker, FastAPI on port 8000)
  - voice-training-db (Railway managed PostgreSQL)

Environment Variables (backend):
  DATABASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
  OPENAI_API_KEY, ANTHROPIC_API_KEY, ELEVENLABS_API_KEY, ALLOWED_ORIGINS,
  TOKEN_BUDGET_QUICK_DRILL, TOKEN_BUDGET_FULL_PRACTICE, TOKEN_BUDGET_CERT_RUN,
  FILLER_TRIGGER_MS (default: 800)

Environment Variables (frontend):
  NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY,
  NEXT_PUBLIC_API_URL, NEXT_PUBLIC_WS_URL
```

### 12.2 Dockerfile (backend)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
# Single worker required: WebSocket connection state is in-process (connections dict).
# Multi-worker requires Redis session registry — deferred to future phase.
```

### 12.3 CI/CD

GitHub Actions on push to `main`:
1. Run backend tests (`pytest`)
2. Run frontend type-check (`tsc --noEmit`)
3. Run frontend tests (`jest`)
4. Build Docker images
5. Deploy to Railway via Railway CLI

---

## 13. Testing Requirements

### 13.1 Backend (pytest)

| Test Suite | Coverage Required |
|------------|------------------|
| Auth middleware | JWT valid, JWT expired, JWT missing, cohort token valid/invalid |
| Rate limiting | >60 req/min blocked, WebSocket connection limit enforced |
| Arc stage tracker | Unit tests with fixture conversation histories (no LLM). Verify all 6 stage transitions and that each unlock condition fires exactly once per satisfied condition. |
| COF gate detection | Unit tests with 50 labeled fixture transcripts. Pass criterion: >= 90% gate agreement with human labels. False positive rate: <= 10% per gate. |
| Metering event writer | Cost computed correctly for each provider |
| Token budget cap | Session terminates gracefully at cap |
| Completion issuance | All conditions met → cert issued; partial conditions → no cert |
| LMS export format | xAPI structure validates against ADL spec |
| Error sanitization | No stack traces in client-facing error responses |
| WebSocket | Connection, message handling, disconnect cleanup |

### 13.2 Frontend (Jest + Testing Library)

| Test Suite | Coverage Required |
|------------|------------------|
| Auth flows | Magic link callback, cohort token join, redirect on unauthenticated |
| Arc progress display | 6 dots render, active dot correct per stage |
| COF gate display | 3 states per gate (pass/fail/pending) |
| Filler audio trigger | Fires at 800ms, not before, not if response arrives first |
| Celebration triggers | Each trigger condition fires correct component |
| Agent preset selection | Token budget and timing applied correctly per preset |
| Mobile layout | Viewport 375px (iPhone SE) renders without overflow |

### 13.3 Integration Tests

- Full session flow: create session → WebSocket conversation → arc completion → cert issued
- Metering pipeline: session creates events → cost rollup correct in admin dashboard
- LMS export: completions table → CSV download → xAPI format validation

### 13.4 Load Test (k6)

- 20 concurrent WebSocket sessions
- Confirm PostgreSQL handles concurrent writes without contention
- Confirm per-session token budget cap fires correctly under load
- Latency budget: platform processing (excluding AI API) p95 < 500ms. End-to-end including AI API p95 < 6s. Load test reports both figures separately. AI API baseline assumed: OpenAI GPT-4o-mini ~1.5s median, ElevenLabs TTS ~1.8s median.

---

## 14. Out of Scope (This Phase)

- Live session monitoring (manager watching in real-time)
- Formal CME/CE accreditation
- Native mobile app (iOS/Android)
- Multi-language support
- BSCI LMS direct xAPI push (CSV export only for pilot)
- Server-side speech transcription (Whisper, Deepgram, etc.). Rep input uses browser Web Speech API only — client-side, no server transcription service required.
- SSO / BSCI corporate identity provider

---

## 15. Open Questions

| Question | Owner | Due |
|----------|-------|-----|
| BSCI Cardiac Rhythm product name and clinical context for arc | Gunter | Before Phase 2 sprint |
| BSCI LMS platform name (Workday, Cornerstone, other) | BSCI L&D contact | Before LMS export sprint |
| BSCI manager email list for initial cohort setup | BSCI project lead | Before launch |
| ElevenLabs voice IDs confirmed for EP Lab Director persona | Dev | Sprint 2 |

---

*LiquidSMARTS™ — Commercial Engineering for Healthcare Technology*
*GFW Management II LLC | gunter@liquidsmarts.com*
