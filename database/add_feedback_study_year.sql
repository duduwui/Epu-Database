-- database/add_feedback_study_year.sql
ALTER TABLE feedback_forms
    ADD COLUMN IF NOT EXISTS study_year VARCHAR(9);  -- e.g. "2025-2026"

-- Backfill existing rows using their created_at year
UPDATE feedback_forms
SET study_year = CONCAT(
    EXTRACT(YEAR FROM created_at)::INT,
    '-',
    EXTRACT(YEAR FROM created_at)::INT + 1
)
WHERE study_year IS NULL;

ALTER TABLE feedback_responses
    ADD COLUMN IF NOT EXISTS snapshot_class_id INTEGER REFERENCES classes(id);

-- Backfill from students table
UPDATE feedback_responses fr
SET snapshot_class_id = s.class_id
FROM students s
WHERE fr.student_id = s.id
  AND fr.snapshot_class_id IS NULL;