-- ============================================================
-- MIGRATION: departments → majors
-- EPU Multi-Major Architecture Rebuild
--
-- What this does:
--   1. Create majors table (colleges = departments grouping only)
--   2. Add major_id FK column to users / classes / subjects
--   3. Create performance indexes
--   4. Truncate all operational data (fresh start)
--   5. Seed 72 majors across 13 colleges
-- ============================================================

SET client_encoding = 'UTF8';

-- ─────────────────────────────────────────────────
-- 1. Create majors table
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS majors (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    code         VARCHAR(20)  UNIQUE NOT NULL,   -- 6-digit numeric string
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    description  TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────
-- 2. Add major_id FK to operational tables
-- ─────────────────────────────────────────────────
ALTER TABLE users    ADD COLUMN IF NOT EXISTS major_id INTEGER REFERENCES majors(id) ON DELETE SET NULL;
ALTER TABLE classes  ADD COLUMN IF NOT EXISTS major_id INTEGER REFERENCES majors(id) ON DELETE SET NULL;
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS major_id INTEGER REFERENCES majors(id) ON DELETE SET NULL;

-- ─────────────────────────────────────────────────
-- 3. Indexes
-- ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_majors_code        ON majors(code);
CREATE INDEX IF NOT EXISTS idx_users_major_id     ON users(major_id);
CREATE INDEX IF NOT EXISTS idx_classes_major_id   ON classes(major_id);
CREATE INDEX IF NOT EXISTS idx_subjects_major_id  ON subjects(major_id);

-- ─────────────────────────────────────────────────
-- 4. Truncate all operational data (fresh start)
--    CASCADE handles all child tables automatically.
-- ─────────────────────────────────────────────────
TRUNCATE TABLE users    RESTART IDENTITY CASCADE;
TRUNCATE TABLE subjects RESTART IDENTITY CASCADE;
TRUNCATE TABLE classes  RESTART IDENTITY CASCADE;

-- ─────────────────────────────────────────────────
-- 5. Seed 72 majors
-- ─────────────────────────────────────────────────

-- College of Health Sciences (CHS)
INSERT INTO majors (name, code, department_id) VALUES
  ('Disease Analysis',       '471832', (SELECT id FROM departments WHERE code = 'CHS')),
  ('Radiology',              '936574', (SELECT id FROM departments WHERE code = 'CHS')),
  ('Physiotherapy',          '284901', (SELECT id FROM departments WHERE code = 'CHS'));

-- College of Engineering (COE)
INSERT INTO majors (name, code, department_id) VALUES
  ('Civil Engineering',      '751346', (SELECT id FROM departments WHERE code = 'COE')),
  ('Roads Engineering',      '619823', (SELECT id FROM departments WHERE code = 'COE')),
  ('Mechanical & Energy',    '483720', (SELECT id FROM departments WHERE code = 'COE'));

-- College of Computer Engineering (CCE)
INSERT INTO majors (name, code, department_id) VALUES
  ('Artificial Intelligence',   '162957', (SELECT id FROM departments WHERE code = 'CCE')),
  ('Information Systems',       '847293', (SELECT id FROM departments WHERE code = 'CCE')),
  ('IT & Communications',       '538461', (SELECT id FROM departments WHERE code = 'CCE'));

-- College of Technology (COT)
INSERT INTO majors (name, code, department_id) VALUES
  ('Materials Technology',      '923784', (SELECT id FROM departments WHERE code = 'COT')),
  ('Geomatics Technology',      '374651', (SELECT id FROM departments WHERE code = 'COT')),
  ('Building Automation',       '891023', (SELECT id FROM departments WHERE code = 'COT')),
  ('Oil Technology',            '456312', (SELECT id FROM departments WHERE code = 'COT')),
  ('Roads Technology',          '712438', (SELECT id FROM departments WHERE code = 'COT')),
  ('Surveying Technology',      '293847', (SELECT id FROM departments WHERE code = 'COT')),
  ('Minerals Technology',       '685321', (SELECT id FROM departments WHERE code = 'COT'));

-- College of Administration (COA)
INSERT INTO majors (name, code, department_id) VALUES
  ('Business Administration',   '147893', (SELECT id FROM departments WHERE code = 'COA')),
  ('Media & Communication',     '829463', (SELECT id FROM departments WHERE code = 'COA')),
  ('Marketing',                 '563817', (SELECT id FROM departments WHERE code = 'COA')),
  ('Accounting',                '394721', (SELECT id FROM departments WHERE code = 'COA'));

-- Medical Institute (PMI)
INSERT INTO majors (name, code, department_id) VALUES
  ('Pharmacy',                  '876543', (SELECT id FROM departments WHERE code = 'PMI')),
  ('Nursing',                   '201984', (SELECT id FROM departments WHERE code = 'PMI')),
  ('Disease Analysis',          '734291', (SELECT id FROM departments WHERE code = 'PMI')),
  ('Midwifery',                 '489172', (SELECT id FROM departments WHERE code = 'PMI')),
  ('Dental Assistance',         '957834', (SELECT id FROM departments WHERE code = 'PMI'));

-- Administrative Institute / Kargeri (MIS)
INSERT INTO majors (name, code, department_id) VALUES
  ('Business Administration',   '312965', (SELECT id FROM departments WHERE code = 'MIS')),
  ('Law Administration',        '678421', (SELECT id FROM departments WHERE code = 'MIS')),
  ('Marketing',                 '845739', (SELECT id FROM departments WHERE code = 'MIS')),
  ('Tourism & Hotels',          '193284', (SELECT id FROM departments WHERE code = 'MIS')),
  ('Management Information Systems', '562781', (SELECT id FROM departments WHERE code = 'MIS')),
  ('Human Resources',           '438927', (SELECT id FROM departments WHERE code = 'MIS')),
  ('Media & Public Relations',  '715362', (SELECT id FROM departments WHERE code = 'MIS')),
  ('Library & Info Science',    '284739', (SELECT id FROM departments WHERE code = 'MIS')),
  ('Accounting',                '961845', (SELECT id FROM departments WHERE code = 'MIS'));

-- Shaqlawa Technical College (STC)
INSERT INTO majors (name, code, department_id) VALUES
  ('Disease Analysis',          '537291', (SELECT id FROM departments WHERE code = 'STC')),
  ('Physical Fitness',          '428163', (SELECT id FROM departments WHERE code = 'STC')),
  ('Nursing',                   '896534', (SELECT id FROM departments WHERE code = 'STC')),
  ('Information Technology',    '173928', (SELECT id FROM departments WHERE code = 'STC')),
  ('Business Administration',   '645782', (SELECT id FROM departments WHERE code = 'STC')),
  ('Management Information Systems', '391847', (SELECT id FROM departments WHERE code = 'STC')),
  ('Tourism & Hotels',          '758234', (SELECT id FROM departments WHERE code = 'STC')),
  ('Building Technology',       '492183', (SELECT id FROM departments WHERE code = 'STC')),
  ('International Diplomacy',   '867341', (SELECT id FROM departments WHERE code = 'STC')),
  ('Architecture Technology',   '235794', (SELECT id FROM departments WHERE code = 'STC')),
  ('Food Technology',           '584912', (SELECT id FROM departments WHERE code = 'STC'));

-- Koya Technical Institute (KTI)
INSERT INTO majors (name, code, department_id) VALUES
  ('Nursing',                   '761438', (SELECT id FROM departments WHERE code = 'KTI')),
  ('Disease Analysis',          '319285', (SELECT id FROM departments WHERE code = 'KTI')),
  ('Obstetrics Technology',     '947261', (SELECT id FROM departments WHERE code = 'KTI')),
  ('Information Technology',    '583749', (SELECT id FROM departments WHERE code = 'KTI')),
  ('Business Administration',   '428031', (SELECT id FROM departments WHERE code = 'KTI')),
  ('Tourism & Hotels',          '691745', (SELECT id FROM departments WHERE code = 'KTI')),
  ('Oil Technology',            '274893', (SELECT id FROM departments WHERE code = 'KTI'));

-- Soran Technical Institute (STI)
INSERT INTO majors (name, code, department_id) VALUES
  ('Nursing',                   '856124', (SELECT id FROM departments WHERE code = 'STI')),
  ('Disease Analysis',          '437291', (SELECT id FROM departments WHERE code = 'STI')),
  ('Obstetrics Technology',     '918573', (SELECT id FROM departments WHERE code = 'STI')),
  ('Business Administration',   '265489', (SELECT id FROM departments WHERE code = 'STI')),
  ('Information Technology',    '784312', (SELECT id FROM departments WHERE code = 'STI')),
  ('Accounting',                '549326', (SELECT id FROM departments WHERE code = 'STI'));

-- Mergasur Technical Institute (MTI)
INSERT INTO majors (name, code, department_id) VALUES
  ('Business Administration',   '671894', (SELECT id FROM departments WHERE code = 'MTI')),
  ('Nursing',                   '238457', (SELECT id FROM departments WHERE code = 'MTI')),
  ('Beekeeping Technology',     '895714', (SELECT id FROM departments WHERE code = 'MTI')),
  ('Veterinary Technology',     '342981', (SELECT id FROM departments WHERE code = 'MTI'));

-- Choman Technical Institute (CTI)
INSERT INTO majors (name, code, department_id) VALUES
  ('Information Technology',    '467823', (SELECT id FROM departments WHERE code = 'CTI')),
  ('Business Administration',   '751394', (SELECT id FROM departments WHERE code = 'CTI')),
  ('Building Technology',       '283916', (SELECT id FROM departments WHERE code = 'CTI')),
  ('Finance Administration',    '614783', (SELECT id FROM departments WHERE code = 'CTI'));

-- Khabat Technical Institute (KHI)
INSERT INTO majors (name, code, department_id) VALUES
  ('Public Health',             '978234', (SELECT id FROM departments WHERE code = 'KHI')),
  ('Information Technology',    '351697', (SELECT id FROM departments WHERE code = 'KHI')),
  ('Law Administration',        '824567', (SELECT id FROM departments WHERE code = 'KHI')),
  ('Veterinary Technology',     '493812', (SELECT id FROM departments WHERE code = 'KHI')),
  ('Plant Protection',          '767341', (SELECT id FROM departments WHERE code = 'KHI')),
  ('Food Safety',               '215948', (SELECT id FROM departments WHERE code = 'KHI'));

-- Verify major count
DO $$
DECLARE cnt INTEGER;
BEGIN
    SELECT COUNT(*) INTO cnt FROM majors;
    RAISE NOTICE 'Total majors seeded: %', cnt;
END $$;
