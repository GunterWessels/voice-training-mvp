# Phase 1 API Contracts — Voice Training Backend

**Branch**: `feat/v2-backend`
**Audience**: Frontend Agent
**Last Updated**: 2026-03-30

---

## 1. New / Modified REST Endpoints

### 1.1 Rep Upload Endpoint (NEW)

```
POST /api/uploads
Content-Type: multipart/form-data
Authorization: Bearer <JWT>
```

**Request body (form fields):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | PDF, DOCX, or TXT only. Max 10MB. |
| `scenario_id` | string (UUID) | No | Associate upload with a specific scenario. |

**Response 200 OK:**

```json
{
    "manifest_id": "550e8400-e29b-41d4-a716-446655440000",
    "chunks_created": 12,
    "filename": "Tria_Stent_IFU.pdf",
    "upload_type": "rep_upload"
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | Unsupported file type (not PDF/DOCX/TXT) |
| 401 | Missing or invalid JWT |
| 403 | User role below `rep` |
| 413 | File exceeds 10MB |
| 422 | Missing `file` field |
| 500 | Internal processing error |

**Notes:**
- Filename is sanitized server-side: path components stripped, only alphanumeric + dot + hyphen allowed.
- All uploads are created with `approved=False`. Admin must explicitly approve before chunks appear in certification mode.
- SHA-256 hash of file contents is stored in manifest for deduplication.

---

## 2. Modified WebSocket Payload Schema

The AI message WebSocket frame (`type: "ai_message"`) is extended with three new fields: `sales_gates`, `post_turn_note`, and `rag_citations`.

### 2.1 Full Extended Payload

```json
{
    "type": "ai_message",
    "text": "That's a reasonable concern. What else worries you about the changeover timeline?",
    "tts_provider": "elevenlabs",
    "audio_b64": "<base64 string or null>",
    "coaching_note": "Try linking this objection back to the patient outcome data.",
    "arc_stage": 2,

    "cof_gates": {
        "clinical": true,
        "operational": false,
        "financial": false
    },

    "spin_gates": {
        "situation": true,
        "problem": true,
        "implication": false,
        "need_payoff": false
    },

    "challenger_gates": {
        "teach": false,
        "tailor": false,
        "take_control": false
    },

    "sales_gates": {
        "start": true,
        "ask_discover": true,
        "ask_dissect": false,
        "ask_develop": false,
        "listen_recap": false,
        "explain_reveal": false,
        "explain_relate": false,
        "secure_what": false,
        "secure_when": false,
        "resistance_empathize": false,
        "resistance_ask": false,
        "resistance_respond": false
    },

    "post_turn_note": "Good Discover question — now push into consequences with a Dissect.",

    "rag_citations": [
        {
            "chunk_id": "550e8400-e29b-41d4-a716-446655440001",
            "source_doc": "Tria Stent IFU",
            "page": 4,
            "approved": true,
            "manifest_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    ]
}
```

### 2.2 Field Definitions

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `sales_gates` | object | Yes (after Phase 1 deploy) | Boolean flags for each SALES framework sub-gate. All keys always present; default false at session start. |
| `post_turn_note` | string | Yes | Short coaching note (max 12 words). Empty string `""` if rep's turn was strong. |
| `rag_citations` | array | Yes | List of RAG chunks used to ground this AI response. Empty array `[]` if no RAG retrieval occurred. |

### 2.3 `sales_gates` Sub-Gate Keys

| Key | SALES Phase | Triggered When |
|-----|-------------|----------------|
| `start` | S — Start | Rep opens with a customer-focused purpose statement |
| `ask_discover` | A — Ask (Discover) | Rep asks current-state discovery questions |
| `ask_dissect` | A — Ask (Dissect) | Rep asks consequence/impact questions |
| `ask_develop` | A — Ask (Develop) | Rep asks solution-direction questions |
| `listen_recap` | L — Listen/Recap | Rep paraphrases or summarizes buyer's words |
| `explain_reveal` | E — Explain (Reveal) | Rep shares clinical insight or 3rd-party evidence |
| `explain_relate` | E — Explain (Relate) | Rep connects evidence back to buyer's stated challenge |
| `secure_what` | S — Secure (What) | Rep states a clear next action |
| `secure_when` | S — Secure (When) | Rep specifies a timeline for the next action |
| `resistance_empathize` | Resistance | Rep acknowledges buyer pushback with empathy |
| `resistance_ask` | Resistance | Rep asks a clarifying question after an objection |
| `resistance_respond` | Resistance | Rep directly responds to the objection |

### 2.4 `rag_citations` Item Schema

```typescript
interface RagCitation {
    chunk_id: string;        // UUID of the knowledge_chunks row
    source_doc: string;      // Human-readable document name
    page: number | null;     // Page number, null if not applicable
    approved: boolean;       // Whether this is an admin-approved claim
    manifest_id: string;     // UUID of the rag_manifest row
}
```

### 2.5 Certification Mode Behavior

When `session_mode == "certification"`:
- `sales_gates`, `spin_gates`, `challenger_gates` are still computed and emitted.
- `post_turn_note` is still generated but the payload includes `"cert_mode": true` alongside it.
- `rag_citations` will only reference chunks where `approved == true`.

---

## 3. New Database Tables

### 3.1 `rag_manifest`

Tracks every file uploaded to the knowledge base.

```sql
CREATE TYPE upload_type_enum AS ENUM ('admin_library', 'rep_upload');

CREATE TABLE rag_manifest (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename     TEXT NOT NULL,
    file_hash    CHAR(64) NOT NULL,              -- SHA-256 hex digest
    uploaded_by  UUID NOT NULL REFERENCES users(id),
    upload_type  upload_type_enum NOT NULL,
    is_active    BOOLEAN DEFAULT true,
    approved     BOOLEAN DEFAULT false,
    approved_by  UUID REFERENCES users(id),
    approved_at  TIMESTAMPTZ,
    session_count INTEGER DEFAULT 0,
    client_id    TEXT,                            -- optional tenant scoping
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rag_manifest_uploaded_by ON rag_manifest(uploaded_by);
CREATE INDEX idx_rag_manifest_is_active ON rag_manifest(is_active) WHERE is_active = true;
```

### 3.2 `rag_retrievals`

Audit log of every RAG retrieval event, regardless of session mode.

```sql
CREATE TYPE session_mode_enum AS ENUM ('practice', 'certification');

CREATE TABLE rag_retrievals (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID NOT NULL REFERENCES sessions(id),
    chunk_id     UUID NOT NULL REFERENCES knowledge_chunks(id),
    query_text   TEXT NOT NULL,
    session_mode session_mode_enum NOT NULL,
    timestamp    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rag_retrievals_session ON rag_retrievals(session_id);
CREATE INDEX idx_rag_retrievals_chunk ON rag_retrievals(chunk_id);
```

### 3.3 Existing Table Alterations

**`sessions` table:**
```sql
ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS session_mode session_mode_enum DEFAULT 'practice';
```

**`completions` table:**
```sql
ALTER TABLE completions
    ADD COLUMN IF NOT EXISTS rag_citations_json JSONB;
```

**`knowledge_chunks` table:**
```sql
ALTER TABLE knowledge_chunks
    ADD COLUMN IF NOT EXISTS manifest_id UUID REFERENCES rag_manifest(id),
    ADD COLUMN IF NOT EXISTS upload_type upload_type_enum DEFAULT 'admin_library';
```

---

## 4. `rag_service.retrieve()` Signature Change

The existing `retrieve()` function gains a `session_mode` parameter:

```python
async def retrieve(
    query: str,
    scenario_id: str,
    domain: str,
    db: AsyncSession,
    top_k: int = 5,
    session_mode: str = "practice",      # NEW
    session_id: str | None = None,       # NEW — for audit logging
) -> List[Dict[str, Any]]
```

**Return schema per item (extended):**

```json
{
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "content": "The Tria stent demonstrated 94% patency at 12 months...",
    "section": "Clinical Evidence",
    "source_doc": "Tria Stent IFU",
    "page": 4,
    "approved_claim": true,
    "approved": true,
    "manifest_id": "550e8400-e29b-41d4-a716-446655440000",
    "similarity": 0.91
}
```

**Certification mode filter (SQL-level):**
```sql
-- Practice mode (default):
WHERE kc.scenario_id = :scenario_id AND kc.domain = :domain

-- Certification mode (additional joins + filters):
WHERE kc.scenario_id = :scenario_id
  AND kc.domain = :domain
  AND kc.approved_claim = true
  AND rm.approved = true
-- (inner JOIN rag_manifest rm ON kc.manifest_id = rm.id)
```

---

## 5. `ai_service.post_turn_coaching()` Signature

New standalone function (does not replace existing `generate_training_turn`):

```python
async def post_turn_coaching(
    rep_text: str,
    conversation_history: list,
    active_gates: dict,           # current sales_gates dict
    session_mode: str,            # "practice" or "certification"
) -> str
```

**Returns:** A single sentence string, max 12 words. Returns `""` if rep's turn requires no coaching.

**When called:** After each rep turn, before the WebSocket payload is assembled. The result goes into `post_turn_note` in the payload.

---

*End of Phase 1 API Contracts*
