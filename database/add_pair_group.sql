-- Add pair_group column to grade_components
-- Allows Report + Seminar (or any two components) to be linked as a paired pair.
-- Components with the same non-null pair_group are AVERAGED for grade calculation.
-- The pair together consumes only ONE slot's weight from the 100% budget.

ALTER TABLE grade_components ADD COLUMN IF NOT EXISTS pair_group INTEGER NULL;

CREATE INDEX IF NOT EXISTS idx_grade_components_pair ON grade_components(subject_id, pair_group)
    WHERE pair_group IS NOT NULL;
