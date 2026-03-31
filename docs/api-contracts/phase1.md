# Phase 1 API Contracts — Voice Training Backend

**Branch**: `feat/v2-backend`
**Audience**: Frontend Agent
**Last Updated**: 2026-03-30 (security review pass applied)

---

## 1. New REST Endpoint

### POST /api/uploads

```
POST /api/uploads
Content-Type: multipart/form-data
Authorization: Bearer <JWT>   (required — 401 if missing)
```

**Request (form fields):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `file` | File | Yes | PDF, DOCX, or TXT only. Max 10 MB. |
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
| 400 | Unsupported extension or magic-byte mismatch |
| 401 | Missing or invalid JWT |
| 403 | Role below `rep` |
| 413 | File > 10 MB (checked during streaming read — no full buffer required) |
| 422 | No extractable text |

**Security notes:**
- File size enforced by streaming read in 64 KB chunks; aborts before full buffer.
- Extension validated against `{.pdf, .docx, .doc, .txt}`.
- Magic bytes (first 512 bytes) validated against known signatures; prevents extension spoofing.
- Filename sanitized: path components stripped, only `[A-Za-z0-9.\-]` allowed.
- SHA-256 hash stored in manifest for deduplication.
- All chunks created with `approved_claim=False` — admin must approve for certification mode.

---

## 2. Modified Session Creation Endpoints

Both session creation endpoints now accept `session_mode`:

### POST /api/sessions (modified)

```json
{
    "persona_id": "clinical_director",
    "scenario_id": "bbe7c082-...",
    "preset": "full_practice",
    "session_mode": "practice"   // NEW — "practice" | "certification", default "practice"
}
```

### POST /api/series/{series_id}/sessions (modified)

```json
{
    "mode": "practice",
    "session_mode": "practice"   // NEW — "practice" | "certification", default "practice"
}
```

`session_mode` is written to the `sessions.session_mode` database column and governs RAG retrieval behavior for the lifetime of the session.

---

## 3. Extended WebSocket Payload

### ai_message frame (full schema)

```json
{
    "type": "ai_message",
    "text": "That's a reasonable concern...",
    "tts_provider": "elevenlabs",
    "audio_b64": "<base64 or null>",
    "coaching_note": "...",
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

    "cert_mode": true,

    "rag_citations": [
        {
            "chunk_id": "550e8400-...",
            "source_doc": "Tria Stent IFU",
            "page": 4,
            "approved": true,
            "manifest_id": "550e8400-..."
        }
    ]
}
```

### New fields

| Field | Type | Always present | Notes |
|-------|------|----------------|-------|
| `sales_gates` | object | Yes (when arc_tracker active) | 12 boolean keys; all false at session start |
| `post_turn_note` | string | Yes | Max 12 words; empty string `""` if no coaching needed |
| `cert_mode` | boolean | Only in certification sessions | Omitted in practice mode |
| `rag_citations` | array | Yes | Empty array `[]` if no RAG retrieval this turn |

---

## 4. New Database Tables

### `rag_manifest`
```sql
CREATE TABLE rag_manifest (
    id            UUID PRIMARY KEY,
    filename      TEXT NOT NULL,
    file_hash     CHAR(64) NOT NULL,   -- SHA-256 hex
    uploaded_by   UUID NOT NULL REFERENCES users(id),
    upload_type   upload_type_enum NOT NULL,
    is_active     BOOLEAN DEFAULT true,
    approved      BOOLEAN DEFAULT false,
    approved_by   UUID REFERENCES users(id),
    approved_at   TIMESTAMPTZ,
    session_count INTEGER DEFAULT 0,
    client_id     TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### `rag_retrievals`
```sql
CREATE TABLE rag_retrievals (
    id           UUID PRIMARY KEY,
    session_id   UUID NOT NULL REFERENCES sessions(id),
    chunk_id     UUID NOT NULL REFERENCES knowledge_chunks(id),
    query_text   TEXT NOT NULL,
    session_mode session_mode_enum NOT NULL,
    timestamp    TIMESTAMPTZ DEFAULT NOW()
);
```

### Enum types
```sql
CREATE TYPE upload_type_enum  AS ENUM ('admin_library', 'rep_upload');
CREATE TYPE session_mode_enum AS ENUM ('practice', 'certification');
```

### Existing table alterations
```sql
ALTER TABLE sessions
    ADD COLUMN session_mode session_mode_enum DEFAULT 'practice';

ALTER TABLE completions
    ADD COLUMN rag_citations_json JSONB;

ALTER TABLE knowledge_chunks
    ADD COLUMN manifest_id UUID REFERENCES rag_manifest(id),
    ADD COLUMN upload_type upload_type_enum DEFAULT 'admin_library';
```

---

## 5. `rag_service.retrieve()` Signature

```python
async def retrieve(
    query: str,
    scenario_id: str,
    domain: str,
    db: AsyncSession,
    top_k: int = 5,
    session_mode: str = "practice",   # NEW
    session_id: str | None = None,    # NEW — for audit logging
) -> List[Dict[str, Any]]
```

Certification mode filter is SQL-level (parameterized JOIN), never a prompt instruction.

---

## 6. `ai_service.post_turn_coaching()` Signature

```python
async def post_turn_coaching(
    rep_text: str,
    conversation_history: list,
    active_gates: dict,       # current sales_gates dict
    session_mode: str,        # "practice" | "certification"
) -> str
```

Returns max-12-word string or `""` if no coaching needed.
