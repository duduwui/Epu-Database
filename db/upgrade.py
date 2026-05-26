from .core import *

def ensure_file_metadata_support():
    """Ensure upload metadata columns are wide enough for real MIME types."""
    global _file_metadata_schema_ready
    if _file_metadata_schema_ready:
        return

    conn = get_db_connection()
    if not conn:
        raise RuntimeError('Database connection unavailable')

    try:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE lecture_files ALTER COLUMN file_type TYPE VARCHAR(255)")
            cur.execute("ALTER TABLE homework ALTER COLUMN file_type TYPE VARCHAR(255)")
            cur.execute("ALTER TABLE homework_submissions ALTER COLUMN file_type TYPE VARCHAR(255)")
        conn.commit()
        _file_metadata_schema_ready = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        return_connection(conn)

def ensure_moodle_assignment_support():
    """Ensure Moodle request and submission support exists without affecting legacy homework pages."""
    global _moodle_assignment_schema_ready
    if _moodle_assignment_schema_ready:
        return

    conn = get_db_connection()
    if not conn:
        raise RuntimeError('Database connection unavailable')

    try:
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE homework ADD COLUMN IF NOT EXISTS due_at TIMESTAMP")
        cursor.execute("ALTER TABLE homework ADD COLUMN IF NOT EXISTS is_moodle_request BOOLEAN DEFAULT FALSE")
        cursor.execute("""
            UPDATE homework
            SET due_at = COALESCE(
                due_at,
                due_date::timestamp + INTERVAL '23 hours 59 minutes'
            )
            WHERE due_at IS NULL
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS homework_submissions (
                id SERIAL PRIMARY KEY,
                homework_id INTEGER NOT NULL REFERENCES homework(id) ON DELETE CASCADE,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                file_name VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_type VARCHAR(255),
                file_size INTEGER DEFAULT 0,
                submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_homework_submissions_homework_student
            ON homework_submissions(homework_id, student_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_homework_moodle_lookup
            ON homework(subject_id, class_id, week_id, due_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_homework_submissions_homework
            ON homework_submissions(homework_id, submitted_at DESC)
        """)
        conn.commit()
        cursor.close()
        return_connection(conn)
        _moodle_assignment_schema_ready = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return_connection(conn)
        raise

def get_current_cycle():
    result = execute_query("SELECT value FROM system_settings WHERE key = 'current_cycle'", fetch_one=True)
    return int(result['value']) if result else 1

def set_current_cycle(cycle):
    execute_query("""INSERT INTO system_settings (key, value, description, updated_at)
        VALUES ('current_cycle', %s, 'Academic cycle', CURRENT_TIMESTAMP)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP""", (str(cycle),))

def ensure_upgrade_tables():
    """Create upgrade-related tables if they don't exist"""
    query = """
    CREATE TABLE IF NOT EXISTS upgrade_history (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        from_semester INTEGER NOT NULL,
        to_semester INTEGER,
        from_year INTEGER,
        to_year INTEGER,
        status VARCHAR(20) NOT NULL DEFAULT 'passed',
        details JSONB,
        upgraded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        upgraded_by INTEGER REFERENCES users(id)
    );
    CREATE INDEX IF NOT EXISTS idx_upgrade_history_student ON upgrade_history(student_id);
    CREATE INDEX IF NOT EXISTS idx_upgrade_history_semester ON upgrade_history(from_semester);
    """
    execute_query(query)

def execute_semester_upgrade(semester, admin_user_id, major_id=None):
    """Promote all passing students from `semester` to `semester+1`.
    Returns counts: {promoted, failed, graduated}.
    """
    import json
    preview = get_semester_upgrade_preview(semester, major_id=major_id)
    promoted_count = 0
    graduated_count = 0

    for stu in preview['passed']:
        old_sem = semester
        new_sem = semester + 1
        old_year = stu.get('year') or (1 if semester <= 2 else 2)

        if semester >= 4:
            # Semester 4 - graduated
            new_sem = None
            new_year = old_year
            status = 'graduated'
            graduated_count += 1
        else:
            new_year = 1 if new_sem <= 2 else 2
            status = 'passed'
            promoted_count += 1

        # Save history
        details = json.dumps({'subjects': stu['subjects']})
        execute_query("""
            INSERT INTO upgrade_history
                (student_id, from_semester, to_semester, from_year, to_year, status, details, upgraded_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
        """, (stu['id'], old_sem, new_sem, old_year, new_year, status, details, admin_user_id))

        if semester >= 4:
            # Mark as graduated
            execute_query("""
                UPDATE students SET semester = NULL, year = %s WHERE id = %s
            """, (new_year, stu['id']))
        else:
            # Promote: update semester, year, lookup new class_id
            new_class = execute_query(
                "SELECT id FROM classes WHERE semester=%s AND shift=%s AND section=%s AND is_active=true"
                + (" AND major_id=%s" if major_id is not None else "")
                + " LIMIT 1",
                ((new_sem, stu['shift'], stu['section'], major_id) if major_id is not None else (new_sem, stu['shift'], stu['section'])),
                fetch_one=True
            )
            new_class_id = new_class['id'] if new_class else None
            execute_query("""
                UPDATE students SET semester=%s, year=%s, class_id=%s WHERE id=%s
            """, (new_sem, new_year, new_class_id, stu['id']))

    # Also record failed students in history
    for stu in preview['failed']:
        details = json.dumps({'subjects': stu.get('subjects', []), 'reason': stu.get('reason', '')})
        execute_query("""
            INSERT INTO upgrade_history
                (student_id, from_semester, to_semester, from_year, to_year, status, details, upgraded_by)
            VALUES (%s, %s, %s, %s, %s, 'failed', %s::jsonb, %s)
        """, (stu['id'], semester, semester, stu.get('year'), stu.get('year'), details, admin_user_id))

    return {
        'promoted': promoted_count,
        'failed': len(preview['failed']),
        'graduated': graduated_count
    }
