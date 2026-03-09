-- Add teacher_type to teacher_assignments
-- Run once: python -c "import db; db.execute_query(open('database/add_teacher_type.sql').read())"
ALTER TABLE teacher_assignments
    ADD COLUMN IF NOT EXISTS teacher_type VARCHAR(20) NOT NULL DEFAULT 'theoretical';
