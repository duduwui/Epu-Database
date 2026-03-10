-- =============================================
-- PERFORMANCE INDEXES
-- Run once on any existing database that was
-- created from schema.sql before this file existed.
-- All statements use IF NOT EXISTS so safe to re-run.
-- =============================================

-- subjects: most-queried table (teacher + semester lookups)
-- NOTE: subjects.class_id was removed during v2 migration; use teacher_assignments for class linkage
CREATE INDEX IF NOT EXISTS idx_subjects_teacher_id        ON subjects(teacher_id);
CREATE INDEX IF NOT EXISTS idx_subjects_practical_teacher_id ON subjects(practical_teacher_id);
CREATE INDEX IF NOT EXISTS idx_subjects_semester           ON subjects(semester);
CREATE INDEX IF NOT EXISTS idx_subjects_results_published  ON subjects(results_published);

-- attendance: subject_id lookups (date + student already indexed)
CREATE INDEX IF NOT EXISTS idx_attendance_subject         ON attendance(subject_id);

-- homework: class, subject, teacher lookups
CREATE INDEX IF NOT EXISTS idx_homework_class_id          ON homework(class_id);
CREATE INDEX IF NOT EXISTS idx_homework_subject_id        ON homework(subject_id);
CREATE INDEX IF NOT EXISTS idx_homework_teacher_id        ON homework(teacher_id);

-- lecture_files: subject and class lookups
CREATE INDEX IF NOT EXISTS idx_lecture_files_subject_id   ON lecture_files(subject_id);
CREATE INDEX IF NOT EXISTS idx_lecture_files_class_id     ON lecture_files(class_id);

-- users: role filter (users page, dashboards)
CREATE INDEX IF NOT EXISTS idx_users_role                 ON users(role);

-- teacher_assignments: separate single-column indexes for flexible filtering
CREATE INDEX IF NOT EXISTS idx_teacher_assignments_teacher_id  ON teacher_assignments(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_assignments_class_id    ON teacher_assignments(class_id);
CREATE INDEX IF NOT EXISTS idx_teacher_assignments_subject_id  ON teacher_assignments(subject_id);

-- timetable: class and teacher schedule lookups
CREATE INDEX IF NOT EXISTS idx_timetable_class_id         ON timetable(class_id);
CREATE INDEX IF NOT EXISTS idx_timetable_teacher_id       ON timetable(teacher_id);

-- weekly_topics: teacher lookup
CREATE INDEX IF NOT EXISTS idx_weekly_topics_teacher_id   ON weekly_topics(teacher_id);

-- grades: teacher_id for teacher grade management
CREATE INDEX IF NOT EXISTS idx_grades_teacher_id          ON grades(teacher_id);

-- classes: year/semester composite filter
CREATE INDEX IF NOT EXISTS idx_classes_year_semester      ON classes(year, semester);

-- grades: student+subject composite (hottest query path — grade pages)
CREATE INDEX IF NOT EXISTS idx_grades_student_subject     ON grades(student_id, subject_id);

-- students: user_id lookup (used on every login + session check)
CREATE INDEX IF NOT EXISTS idx_students_user_id           ON students(user_id);

-- teachers: user_id lookup (same reason as above)
CREATE INDEX IF NOT EXISTS idx_teachers_user_id           ON teachers(user_id);

-- weekly_topics: class+subject composite (topics page loads both)
CREATE INDEX IF NOT EXISTS idx_weekly_topics_class_subject ON weekly_topics(class_id, subject_id);
