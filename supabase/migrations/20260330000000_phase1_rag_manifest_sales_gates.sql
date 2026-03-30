-- Migration 003: Phase 1 — RAG Manifest, Retrieval Audit, SALES Gates
-- Voice Training Platform — Backend Phase 1
-- Apply: psql $DATABASE_URL -f migrations/versions/003_phase1_rag_manifest_sales_gates.sql

BEGIN;

-- ============================================================
-- Step 1: Create shared ENUM types (idempotent)
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'upload_type_enum') THEN
        CREATE TYPE upload_type_enum AS ENUM ('admin_library', 'rep_upload');
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'session_mode_enum') THEN
        CREATE TYPE session_mode_enum AS ENUM ('practice', 'certification');
    END IF;
END
$$;

-- ============================================================
-- Step 2: Create rag_manifest table
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_manifest (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename      TEXT NOT NULL,
    file_hash     CHAR(64) NOT NULL,                          -- SHA-256 hex digest
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

CREATE INDEX IF NOT EXISTS idx_rag_manifest_uploaded_by
    ON rag_manifest(uploaded_by);

CREATE INDEX IF NOT EXISTS idx_rag_manifest_active
    ON rag_manifest(is_active)
    WHERE is_active = true;

-- ============================================================
-- Step 3: Add new columns to knowledge_chunks
-- ============================================================
ALTER TABLE knowledge_chunks
    ADD COLUMN IF NOT EXISTS manifest_id UUID REFERENCES rag_manifest(id),
    ADD COLUMN IF NOT EXISTS upload_type upload_type_enum DEFAULT 'admin_library';

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_manifest
    ON knowledge_chunks(manifest_id);

-- ============================================================
-- Step 4: Create rag_retrievals audit table
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_retrievals (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID NOT NULL REFERENCES sessions(id),
    chunk_id     TEXT NOT NULL REFERENCES knowledge_chunks(id),
    query_text   TEXT NOT NULL,
    session_mode session_mode_enum NOT NULL,
    timestamp    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rag_retrievals_session
    ON rag_retrievals(session_id);

CREATE INDEX IF NOT EXISTS idx_rag_retrievals_chunk
    ON rag_retrievals(chunk_id);

-- ============================================================
-- Step 5: Extend existing tables
-- ============================================================

-- sessions: add session_mode column
ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS session_mode session_mode_enum DEFAULT 'practice';

-- completions: add rag_citations_json column
ALTER TABLE completions
    ADD COLUMN IF NOT EXISTS rag_citations_json JSONB;

COMMIT;
