-- Add credits column to subjects table
ALTER TABLE subjects
ADD COLUMN credits INTEGER DEFAULT 3 CHECK (credits > 0 AND credits <= 30);

-- Update existing subjects with default credits
UPDATE subjects SET credits = 6 WHERE credits IS NULL;
