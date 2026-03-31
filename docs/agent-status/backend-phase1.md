# Backend Agent — Phase 1 Status (Security Review Pass)

**Branch**: `feat/v2-backend`
**Date**: 2026-03-30
**Agent**: Backend Agent (Claude Sonnet 4.6)
**Tests**: 54 passed, 0 failed

---

## What Was Built

### Phase 1 Core (original)

1. **SALES Gate Detection** (`arc_engine.py`) — `SALES_SEEDS` dict with 12 sub-gates; `ConditionEvaluator.sales_flags()` and `ArcStageTracker` tracking. SPIN_SEEDS and CHALLENGER_SEEDS also added (were missing from this branch's baseline).

2. **Post-Turn Coaching** (`ai_service.py`) — `post_turn_coaching()` async method; mock implementation for offline environments.

3. **Database Models** (`models.py`) — `RagManifest`, `RagRetrieval` ORM classes; `Session.session_mode`, `Completion.rag_citations_json`, `KnowledgeChunk.manifest_id`/`upload_type`.

4. **SQL Migration** (`migrations/versions/003_phase1_rag_manifest_sales_gates.sql`) — idempotent DDL for enum types, new tables, and column additions. Apply: `psql $DATABASE_URL -f migrations/versions/003_phase1_rag_manifest_sales_gates.sql`

5. **RAG Service** (`rag_service.py`) — `session_mode` + `session_id` params; certification mode uses parameterized SQL INNER JOIN; audit logging to `rag_retrievals`.

6. **WebSocket Payload** (`main.py`) — `sales_gates`, `post_turn_note`, `cert_mode`, `rag_citations` added to `ai_message` frame.

---

## Security Review Fixes Applied

### BLOCK-2 — WebSocket always requires authentication
**File**: `main.py` ~line 1033

Replaced the `if token:` opt-in guard with a hard rejection:
```python
if not token:
    await websocket.close(code=4001)
    return
ws_user = await verify_ws_token(token)
if not ws_user:
    await websocket.close(code=4001)
    return
```
Empty or invalid tokens are now rejected before `websocket.accept()` is called. There is no unauthenticated path.

### BLOCK-3A — `session_mode` written to session record
**File**: `main.py`

- Added `session_mode: str = "practice"` to `ApiSessionCreate` Pydantic model.
- Added `session_mode: str = "practice"` to `StartSessionRequest` Pydantic model.
- Both `create_api_session()` and `start_series_session()` now write `session_mode=body.session_mode` when constructing the `SessionModel` ORM object.
- Without this fix, `pg_session.session_mode` was always `NULL`; the certification filter in `rag_service.retrieve()` was unreachable.

### BLOCK-3B — `session_mode` and `session_id` passed to `retrieve()`
**File**: `main.py` ~line 1290

RAG retrieve call now passes:
```python
session_mode=pg_session.session_mode or "practice",
session_id=str(pg_session.id),
```
This activates the SQL-level approved_claim + manifest.approved filter in certification mode, and enables retrieval audit logging.

### BLOCK-4 — Admin/manager endpoints have role enforcement
**File**: `main.py`

`require_role()` (already in `auth.py`) applied to all four endpoints:

| Endpoint | Before | After |
|----------|--------|-------|
| `GET /api/admin/sessions` | `get_current_user` | `require_role("admin")` |
| `GET /api/manager/cohort` | `get_current_user` | `require_role("manager", "admin")` |
| `GET /api/manager/export` | `get_current_user` | `require_role("manager", "admin")` |
| `GET /api/admin/metrics` | `get_current_user` | `require_role("admin")` |

`require_role` is now imported from `auth.py` in the main.py import line.

### ADV-1 — Upload size checked before full read; magic-byte validation
**File**: `main.py` upload endpoint

- **Size check before buffer**: File is read in 64 KB chunks; raises HTTP 413 as soon as cumulative bytes exceed 10 MB. No full buffer is held.
- **Magic-byte validation**: First 512 bytes checked against known signatures (`%PDF` for PDF, `PK\x03\x04` for DOCX). Extension spoofing (e.g., renaming `.exe` to `.pdf`) raises HTTP 400.
- **Dead code removed**: The original `_ALLOWED_MIME_TYPES` dict is replaced by `_MAGIC_SIGNATURES`, which is actually used in `_sniff_extension()`.

### ADV-2 — `datetime.utcnow` replaced with `datetime.now(timezone.utc)`
**File**: `models.py`

Both `RagManifest.created_at` and `RagRetrieval.timestamp` defaults now use:
```python
default=lambda: datetime.now(timezone.utc)
```
`from datetime import timezone` added to imports. Lambda prevents a single datetime instance being shared across rows.

### ADV-5 — Dead `_ALLOWED_MIME_TYPES` dict removed
**File**: `main.py`

Replaced entirely by `_MAGIC_SIGNATURES` which is used in `_sniff_extension()`. No dead code remains.

---

## Test Results

```
54 passed, 5 warnings in 16.02s
```

New tests added in this pass (8):
- `test_websocket_rejects_empty_token` — BLOCK-2 coverage
- `test_admin_sessions_requires_admin_role` — BLOCK-4
- `test_manager_cohort_requires_manager_role` — BLOCK-4
- `test_manager_export_requires_manager_role` — BLOCK-4
- `test_admin_metrics_requires_admin_role` — BLOCK-4
- `test_admin_role_can_access_admin_sessions` — positive path for BLOCK-4
- `test_spin_flags_present` — validates SPIN gate initialization
- `test_challenger_flags_present` — validates Challenger gate initialization

---

## Known Issues

None. All 54 tests pass. No regressions.
