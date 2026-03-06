-- =============================================
-- EXAM PERIODS & EXAM SIGNUPS TABLES
-- Admin opens exam periods for final / second_round exams
-- Students sign up for exams during active periods
-- =============================================

-- Exam periods: time windows for final exams and second-round exams
CREATE TABLE IF NOT EXISTS exam_periods (
    id SERIAL PRIMARY KEY,
    semester INTEGER NOT NULL,
    period_type VARCHAR(20) NOT NULL CHECK (period_type IN ('final', 'second_round')),
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (end_date > start_date)
);

CREATE INDEX IF NOT EXISTS idx_exam_periods_semester ON exam_periods(semester);
CREATE INDEX IF NOT EXISTS idx_exam_periods_type ON exam_periods(period_type);
CREATE INDEX IF NOT EXISTS idx_exam_periods_dates ON exam_periods(start_date, end_date);

-- Exam signups: which students signed up for which exam
CREATE TABLE IF NOT EXISTS exam_signups (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    exam_type VARCHAR(20) NOT NULL CHECK (exam_type IN ('final', 'second_round')),
    signed_up_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(student_id, subject_id, exam_type)
);

CREATE INDEX IF NOT EXISTS idx_exam_signups_student ON exam_signups(student_id);
CREATE INDEX IF NOT EXISTS idx_exam_signups_subject ON exam_signups(subject_id);
