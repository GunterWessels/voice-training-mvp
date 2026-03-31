-- Migration 004: Add persona_id to sessions table
-- Allows storing which buyer persona the rep selected when creating a session.
-- Nullable with default 'vac_buyer' so existing rows are unaffected.

ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS persona_id TEXT NOT NULL DEFAULT 'vac_buyer';
