-- Voice Training Platform — Initial Schema
-- PostgreSQL 14+

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Divisions (BSCI commercial divisions)
CREATE TABLE divisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cohorts (training groups within a division)
-- manager_id FK to users added below after users table is created
CREATE TABLE cohorts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    division_id UUID NOT NULL REFERENCES divisions(id),
    cohort_token TEXT UNIQUE,
    celebrations_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users (populated from Supabase Auth)
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    role TEXT NOT NULL DEFAULT 'rep',
    cohort_id UUID REFERENCES cohorts(id),
    division_id UUID REFERENCES divisions(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ
);

-- Add manager_id FK now that users table exists
ALTER TABLE cohorts ADD COLUMN manager_id UUID REFERENCES users(id);

-- Scenarios (choreographed product scenarios)
CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    division_id UUID NOT NULL REFERENCES divisions(id),
    product_name TEXT,
    persona_id TEXT NOT NULL,
    arc JSONB NOT NULL,
    celebration_triggers JSONB,
    cartridge_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions (one per training conversation)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    scenario_id UUID NOT NULL REFERENCES scenarios(id),
    preset TEXT DEFAULT 'full_practice',
    status TEXT DEFAULT 'active',
    arc_stage_reached INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER
);

-- Messages (conversation turns)
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id),
    speaker TEXT NOT NULL,
    text TEXT NOT NULL,
    arc_stage INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Completions
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
    provider TEXT NOT NULL,
    model TEXT,
    call_type TEXT,
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

-- Practice Series Items (explicit ordered list)
CREATE TABLE practice_series_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_id UUID NOT NULL REFERENCES practice_series(id) ON DELETE CASCADE,
    scenario_id UUID NOT NULL REFERENCES scenarios(id),
    position INTEGER NOT NULL,
    UNIQUE (series_id, position)
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_scenario_id ON sessions(scenario_id);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_metering_events_session_id ON metering_events(session_id);
CREATE INDEX idx_metering_events_timestamp ON metering_events(timestamp);
