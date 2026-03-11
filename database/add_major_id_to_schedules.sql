-- Add major_id to class_schedules so each major has its own schedule per semester/shift/section
ALTER TABLE class_schedules ADD COLUMN IF NOT EXISTS major_id INTEGER REFERENCES majors(id);

-- Drop the old unique constraint (semester, shift, section)
ALTER TABLE class_schedules DROP CONSTRAINT IF EXISTS class_schedules_semester_shift_section_key;

-- Add new unique constraint that includes major_id
ALTER TABLE class_schedules DROP CONSTRAINT IF EXISTS class_schedules_major_semester_shift_section_key;
ALTER TABLE class_schedules ADD CONSTRAINT class_schedules_major_semester_shift_section_key
    UNIQUE (major_id, semester, shift, section);

-- Delete existing schedules that have no major_id (they are now orphaned/invalid)
DELETE FROM class_schedules WHERE major_id IS NULL;
