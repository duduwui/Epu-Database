-- database/add_moodle_features.sql

-- 1. Create the custom Weeks/Blocks table so teachers can define their own timeline
CREATE TABLE IF NOT EXISTS moodle_weeks (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL, -- e.g., "Week 1: Introduction", "Block A"
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Modify lecture_files to attach to weeks, and support Links
ALTER TABLE lecture_files 
ADD COLUMN IF NOT EXISTS week_id INTEGER REFERENCES moodle_weeks(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS is_link BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS link_url VARCHAR(500);

-- 3. Modify homework to attach to weeks
ALTER TABLE homework 
ADD COLUMN IF NOT EXISTS week_id INTEGER REFERENCES moodle_weeks(id) ON DELETE SET NULL;

-- 4. Create internal engagement tracker for students
CREATE TABLE IF NOT EXISTS student_engagement (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    access_date DATE NOT NULL DEFAULT CURRENT_DATE,
    time_spent_seconds INTEGER NOT NULL DEFAULT 0,
    UNIQUE (student_id, subject_id, class_id, access_date)
);

-- Indexes to speed up queries for Moodle Dashboards
CREATE INDEX IF NOT EXISTS idx_moodle_weeks_query ON moodle_weeks(class_id, subject_id);
CREATE INDEX IF NOT EXISTS idx_student_engagement ON student_engagement(student_id, class_id);
