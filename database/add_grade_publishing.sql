-- Add publishing control for grades and results
-- This allows teachers to save grades as draft and publish when ready
-- Admin controls final results visibility

-- Add published field to grades table (default false - draft mode)
ALTER TABLE grades 
ADD COLUMN IF NOT EXISTS published BOOLEAN DEFAULT FALSE;

-- Add results_published field to subjects table
-- This controls whether final results/transcript is visible to students
ALTER TABLE subjects 
ADD COLUMN IF NOT EXISTS results_published BOOLEAN DEFAULT FALSE;

-- Create index for efficient querying of published grades
CREATE INDEX IF NOT EXISTS idx_grades_published ON grades(published);
CREATE INDEX IF NOT EXISTS idx_subjects_results_published ON subjects(results_published);

-- Update existing grades to published (for backward compatibility)
UPDATE grades SET published = TRUE WHERE published IS NULL;
