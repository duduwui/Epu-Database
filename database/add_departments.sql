-- =============================================
-- DEPARTMENTS TABLE (Multi-Major Expansion Foundation)
-- Enables MIS, IS, CS, and any future majors to share the same
-- app while staying fully isolated at the data level.
--
-- Currently all existing data is implicitly one department.
-- When you're ready to expand: create departments, then run
--   UPDATE classes SET department_id = X WHERE ...
--   UPDATE subjects SET department_id = X WHERE ...
--   UPDATE users SET department_id = X WHERE ...
-- and add WHERE department_id = current_user.department_id
-- to any query that should be department-scoped.
-- =============================================

CREATE TABLE IF NOT EXISTS departments (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20)  NOT NULL UNIQUE,   -- short name, e.g. "MIS", "IS", "CS"
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link classes to a department (NULL = not yet assigned / single-major mode)
ALTER TABLE classes  ADD COLUMN IF NOT EXISTS department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL;

-- Link subjects to a department
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL;

-- Link users (students & teachers & admins) to a department
ALTER TABLE users    ADD COLUMN IF NOT EXISTS department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL;

-- =============================================
-- INDEXES — fast WHERE department_id = X at scale
-- =============================================
CREATE INDEX IF NOT EXISTS idx_departments_code         ON departments(code);
CREATE INDEX IF NOT EXISTS idx_classes_department_id    ON classes(department_id);
CREATE INDEX IF NOT EXISTS idx_subjects_department_id   ON subjects(department_id);
CREATE INDEX IF NOT EXISTS idx_users_department_id      ON users(department_id);
