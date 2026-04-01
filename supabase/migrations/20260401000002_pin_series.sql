-- Add pinned flag to practice_series; pinned series sort first as "Today's Assignment"
ALTER TABLE practice_series ADD COLUMN IF NOT EXISTS pinned BOOLEAN NOT NULL DEFAULT false;

-- Pin the LithoVue Elite HCRU series for all participants
UPDATE practice_series
SET pinned = true
WHERE id = 'f1a00000-0000-0000-0000-000000000002';
