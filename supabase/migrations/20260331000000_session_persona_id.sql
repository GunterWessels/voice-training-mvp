-- Migration: add persona_id to sessions
-- Allows storing which buyer persona the rep selected at session creation.
ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS persona_id TEXT NOT NULL DEFAULT 'vac_buyer';
