# Backend Agent — Phase 1 Status

**Branch**: `feat/v2-backend`
**Date**: 2026-03-30
**Agent**: Backend Agent (Claude Sonnet 4.6)

---

## What Was Built

### 1. SALES Gate Detection (`arc_engine.py`)
- Added `SALES_SEEDS` dictionary with 12 sub-gates: Start, Ask (Discover/Dissect/Develop), Listen/Recap, Explain (Reveal/Relate), Secure (What/When), and Resistance (Empathize/Ask/Respond).
- Added `ConditionEvaluator.sales_flags(history)` — parallel to existing `spin_flags` and `challenger_flags`.
- Updated `ArcStageTracker.__init__` to initialize `self.sales_flags` with all 12 keys defaulted to `False`.
- Updated `ArcStageTracker._update_cof_flags` to call `ev.sales_flags(history)` on every turn.

### 2. Post-Turn Coaching (`ai_service.py`)
- Added `AIService.post_turn_coaching(rep_text, conversation_history, active_gates, session_mode) -> str`.
- Returns a max-12-word coaching sentence or empty string if no coaching is needed.
- Mock implementation (`_mock_post_turn_coaching`) walks the SALES phase sequence and returns deterministic coaching without an API key.
- Real implementation calls `_call_provider` with a compact system prompt targeting 40 max tokens at temperature 0.3.

### 3. Database Models (`models.py`)
- Added `upload_type_enum` and `session_mode_enum` SQLAlchemy enum types (mapped to PostgreSQL enums, `create_type=False`).
- Added `RagManifest` model (`rag_manifest` table).
- Added `RagRetrieval` model (`rag_retrievals` table).
- Extended `Session` with `session_mode` column.
- Extended `Completion` with `rag_citations_json` column.
- Extended `KnowledgeChunk` with `manifest_id` and `upload_type` columns.

### 4. Migration (`migrations/versions/003_phase1_rag_manifest_sales_gates.sql`)
- Creates `upload_type_enum` and `session_mode_enum` PostgreSQL types (idempotent with `DO $$ IF NOT EXISTS` blocks).
- Creates `rag_manifest` table with all required columns and indexes.
- Adds `manifest_id` and `upload_type` columns to `knowledge_chunks`.
- Creates `rag_retrievals` table.
- Adds `session_mode` to `sessions` and `rag_citations_json` to `completions`.
- Note: this is a plain SQL migration (the project uses raw SQL migrations in `migrations/`, not Alembic Python migrations). The file is idempotent — all DDL uses `IF NOT EXISTS`.

### 5. RAG Service (`rag_service.py`)
- Extended `retrieve()` with `session_mode` and `session_id` parameters.
- Certification mode filter: `INNER JOIN rag_manifest ... AND kc.approved_claim = true AND rm.approved = true` — implemented as parameterized SQL, never string interpolation.
- Practice mode: LEFT JOIN to rag_manifest to still surface `manifest_id` / `approved` metadata.
- Returns extended dict per chunk: `chunk_id`, `source_doc`, `page`, `approved_claim`, `approved`, `manifest_id`, `similarity`.
- Audit logging: `_log_retrievals()` writes every retrieval to `rag_retrievals` when `session_id` is provided.

### 6. Rep Upload Endpoint (`main.py`)
- `POST /api/uploads` with JWT auth, `get_current_user` dependency.
- File type validation (PDF/DOCX/TXT), 10MB size limit, filename sanitization.
- Processing pipeline: read bytes, SHA-256 hash, extract text via `extractor.py`, chunk (~400 words), embed (text-embedding-3-small), write `knowledge_chunks` + `rag_manifest`.
- All chunks created with `approved_claim=False`, `upload_type='rep_upload'`.

### 7. WebSocket Payload Extension (`main.py`)
- Added `sales_gates` (all 12 keys) to `message_data` when `arc_tracker` is available.
- Added `post_turn_note` — result of `ai_service.post_turn_coaching()`, always present (empty string if no coaching).
- Added `cert_mode: true` when `session_mode == "certification"`.
- Added `rag_citations` list — materializes chunk metadata from `_rag_chunks`.

### 8. API Contracts (`docs/api-contracts/phase1.md`)
- Full REST endpoint spec for `POST /api/uploads`.
- Extended WebSocket payload schema with all new fields.
- New table DDL for `rag_manifest` and `rag_retrievals`.
- `retrieve()` signature change and return schema.
- `post_turn_coaching()` signature and behavior spec.

---

## Test Results

```
46 passed, 5 warnings in 16.14s
```

New tests (22): All 12 SALES gate detections, ArcStageTracker initialization and update, 4 post_turn_coaching mock tests, 3 upload endpoint auth/validation tests.

Existing tests (24): All passing — no regressions.

---

## Deviations from Plan

1. **Migration format**: The project uses plain SQL files in `migrations/` (not Alembic Python files with `alembic upgrade head`). Created `003_phase1_rag_manifest_sales_gates.sql` consistent with `001_initial.sql` and `002_rag.sql`. Command to apply: `psql $DATABASE_URL -f migrations/versions/003_phase1_rag_manifest_sales_gates.sql`.

2. **`knowledge_chunks` FK to `rag_manifest`**: The FK `REFERENCES rag_manifest(id)` is added only after the manifest table is created in the same migration. Pre-Phase 1 chunks (no `manifest_id`) remain valid — the column is nullable and the certification mode query uses `INNER JOIN` which naturally excludes them.

3. **`_rag_chunks` variable in WebSocket handler**: The `_rag_chunks` variable is set by the existing RAG retrieval block earlier in the handler. The `rag_citations` payload pulls from this variable. If retrieval did not run (e.g., early ARC stages), `_rag_chunks` is empty and `rag_citations` is `[]`.

---

## Known Issues

None. All tests pass.
