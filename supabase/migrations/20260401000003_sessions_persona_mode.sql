-- Add persona_id and session_mode to sessions table
-- persona_id: which buyer persona the rep selected (drives AI character)
-- session_mode: practice | certification (drives RAG filtering)
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS persona_id TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS session_mode TEXT DEFAULT 'practice';
