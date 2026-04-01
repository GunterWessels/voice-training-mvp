-- Migration: seed practice_series for Tria Stents scenario
-- Creates the first library entry so the Content Library shows content.

-- Add category column to practice_series (used by ContentLibrary to filter by product area)
ALTER TABLE practice_series
    ADD COLUMN IF NOT EXISTS category TEXT,
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT true;

-- Seed: Tria Stents practice series (Stone Management category)
INSERT INTO practice_series (id, name, category, description, approved, created_at)
VALUES (
    'f1a00000-0000-0000-0000-000000000001',
    'Tria Stents — Urology',
    'stone_management',
    'Practice selling Tria ureteral stents to a high-volume urologist. Master the COF bridge and SALES framework across 6 progressive ARC stages.',
    true,
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    name        = EXCLUDED.name,
    category    = EXCLUDED.category,
    description = EXCLUDED.description;

-- Link series to Tria scenario
INSERT INTO practice_series_items (id, series_id, scenario_id, position)
VALUES (
    'f2a00000-0000-0000-0000-000000000001',
    'f1a00000-0000-0000-0000-000000000001',
    'bbe7c082-687f-4b62-9b3e-69e1bd87537c',
    1
)
ON CONFLICT (series_id, position) DO NOTHING;
