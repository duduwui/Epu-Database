from .core import *

def ensure_teacher_assignment_support():
    """Ensure teacher assignment table matches the current app contract."""
    global _teacher_assignment_schema_ready
    if _teacher_assignment_schema_ready:
        return

    conn = get_db_connection()
    if not conn:
        raise RuntimeError('Database connection unavailable')

    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM teacher_assignments ta
                USING teacher_assignments dup
                WHERE ta.id < dup.id
                  AND ta.teacher_id = dup.teacher_id
                  AND ta.subject_id = dup.subject_id
                  AND COALESCE(ta.class_id, -1) = COALESCE(dup.class_id, -1)
            """)

            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'teacher_assignments_shift_check') THEN
                        ALTER TABLE teacher_assignments DROP CONSTRAINT teacher_assignments_shift_check;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'students_shift_check') THEN
                        ALTER TABLE students DROP CONSTRAINT students_shift_check;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_shift') THEN
                        ALTER TABLE classes DROP CONSTRAINT check_shift;
                    END IF;
                END $$;
            """)

            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'teacher_assignments_shift_check') THEN
                        ALTER TABLE teacher_assignments
                        ADD CONSTRAINT teacher_assignments_shift_check
                        CHECK (shift IN ('morning', 'evening', 'night'));
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'students_shift_check') THEN
                        ALTER TABLE students
                        ADD CONSTRAINT students_shift_check
                        CHECK (shift IN ('morning', 'evening', 'night'));
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_shift') THEN
                        ALTER TABLE classes
                        ADD CONSTRAINT check_shift
                        CHECK (shift IN ('morning', 'evening', 'night'));
                    END IF;
                END $$;
            """)

            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_teacher_assignments_teacher_subject_class
                ON teacher_assignments (teacher_id, subject_id, class_id)
            """)

            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'teacher_assignments_class_id_fkey'
                    ) THEN
                        ALTER TABLE teacher_assignments
                        ADD CONSTRAINT teacher_assignments_class_id_fkey
                        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE;
                    END IF;
                END $$;
            """)

        conn.commit()
        _teacher_assignment_schema_ready = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        return_connection(conn)

def create_teacher(user_id, department=None, phone=None): return execute_insert_returning("INSERT INTO teachers (user_id, department, phone) VALUES (%s,%s,%s) RETURNING id", (user_id, department, phone))

def get_all_teachers(major_id=None):
    if major_id: return execute_query("SELECT t.*, u.full_name, u.username, u.email FROM teachers t JOIN users u ON t.user_id=u.id WHERE u.major_id=%s ORDER BY u.full_name", (major_id,), fetch_all=True)
    return execute_query("SELECT t.*, u.full_name, u.username, u.email FROM teachers t JOIN users u ON t.user_id=u.id ORDER BY u.full_name", fetch_all=True)

def get_all_teachers_with_subjects(major_id=None):
    if major_id: return execute_query("SELECT t.id as teacher_id, t.user_id, t.department, t.phone, u.full_name, u.username, u.email, COALESCE((SELECT COUNT(*) FROM subjects WHERE teacher_id=t.id),0) as subject_count FROM teachers t JOIN users u ON t.user_id=u.id WHERE u.major_id=%s ORDER BY u.full_name", (major_id,), fetch_all=True)
    return execute_query("SELECT t.id as teacher_id, t.user_id, t.department, t.phone, u.full_name, u.username, u.email, COALESCE((SELECT COUNT(*) FROM subjects WHERE teacher_id=t.id),0) as subject_count FROM teachers t JOIN users u ON t.user_id=u.id ORDER BY u.full_name", fetch_all=True)

def get_subjects_by_teacher_id(teacher_id):
    results = execute_query("SELECT s.id, s.name, c.name as class_name, c.year, c.semester, c.section, c.shift, ta.id as assignment_id, ta.teacher_type FROM teacher_assignments ta JOIN subjects s ON ta.subject_id=s.id JOIN classes c ON ta.class_id=c.id WHERE ta.teacher_id=%s ORDER BY s.name, c.year, c.section", (teacher_id,), fetch_all=True)
    if results: return results
    return execute_query("SELECT s.id, s.name, 'Semester '||s.semester AS class_name, NULL::int AS year, s.semester, NULL::varchar AS section, NULL::varchar AS shift, NULL::int AS assignment_id FROM subjects s WHERE s.teacher_id=%s ORDER BY s.semester, s.name", (teacher_id,), fetch_all=True)

def get_subjects_by_teacher(teacher_id):
    results = execute_query("SELECT DISTINCT s.*, c.name as class_name, c.year, c.semester, c.section, c.shift, ta.id as assignment_id, ta.class_id FROM subjects s JOIN teacher_assignments ta ON s.id=ta.subject_id JOIN classes c ON ta.class_id=c.id WHERE ta.teacher_id=%s ORDER BY c.year, c.semester, c.section, s.name", (teacher_id,), fetch_all=True)
    if results: return results
    return execute_query("SELECT DISTINCT s.*, 'Semester '||s.semester AS class_name, NULL::int AS year, s.semester, NULL::varchar AS section, NULL::varchar AS shift, NULL::int AS assignment_id, NULL::int AS class_id FROM subjects s WHERE s.teacher_id=%s ORDER BY s.semester, s.name", (teacher_id,), fetch_all=True)

def update_subject_teacher(assignment_id, teacher_id): return execute_query("UPDATE teacher_assignments SET teacher_id=%s WHERE id=%s", (teacher_id, assignment_id))

def get_teacher_dashboard_groups(teacher_id):
    """Get teacher teaching groups with live student/component counts."""
    query = """
        SELECT ta.subject_id,
               ta.class_id,
               s.name AS subject_name,
               s.credits,
               c.name AS class_name,
               c.year,
               c.semester,
               c.section,
               c.shift,
               COUNT(DISTINCT st.id) AS student_count,
               COALESCE(gc.component_count, 0) AS component_count
        FROM teacher_assignments ta
        JOIN subjects s ON ta.subject_id = s.id
        JOIN classes c ON ta.class_id = c.id
        LEFT JOIN student_enrollments se ON se.subject_id = ta.subject_id
        LEFT JOIN students st ON st.id = se.student_id AND st.class_id = ta.class_id
        LEFT JOIN (
            SELECT subject_id, COUNT(*) AS component_count
            FROM grade_components
            GROUP BY subject_id
        ) gc ON gc.subject_id = s.id
        WHERE ta.teacher_id = %s
        GROUP BY ta.subject_id, ta.class_id, s.name, s.credits, c.name, c.year, c.semester, c.section, c.shift, gc.component_count
        ORDER BY c.year, c.semester, c.shift, c.section, s.name
    """
    return execute_query(query, (teacher_id,), fetch_all=True) or []

def get_teacher_subject_groups(teacher_id):
    """Group a teacher's assignments by subject for dashboard and Moodle selection UIs."""
    groups = get_teacher_dashboard_groups(teacher_id) or []
    grouped = {}

    for row in groups:
        subject_id = row['subject_id']
        entry = grouped.setdefault(subject_id, {
            'subject_id': subject_id,
            'subject_name': row.get('subject_name'),
            'credits': row.get('credits'),
            'semester': row.get('semester'),
            'class_count': 0,
            'total_students': 0,
            'component_count': row.get('component_count') or 0,
            'shifts': [],
            'assignments': [],
        })

        shift_value = row.get('shift')
        if shift_value and shift_value not in entry['shifts']:
            entry['shifts'].append(shift_value)

        assignment = {
            'subject_id': subject_id,
            'class_id': row.get('class_id'),
            'class_name': row.get('class_name'),
            'year': row.get('year'),
            'semester': row.get('semester'),
            'section': row.get('section'),
            'shift': row.get('shift'),
            'student_count': row.get('student_count') or 0,
            'component_count': row.get('component_count') or 0,
        }
        entry['assignments'].append(assignment)
        entry['class_count'] += 1
        entry['total_students'] += assignment['student_count']

    results = list(grouped.values())
    for item in results:
        item['assignments'].sort(key=lambda a: (
            a.get('semester') or 0,
            (a.get('shift') or ''),
            (a.get('section') or '')
        ))
        item['shifts_label'] = ', '.join(shift.title() for shift in item['shifts']) if item['shifts'] else '-'

    results.sort(key=lambda item: ((item.get('semester') or 0), item.get('subject_name') or ''))
    return results

def get_teacher_subject_assignments(teacher_id, subject_id):
    """Get dashboard assignment rows for one subject assigned to the teacher."""
    groups = get_teacher_dashboard_groups(teacher_id) or []
    assignments = [row for row in groups if row.get('subject_id') == subject_id]
    assignments.sort(key=lambda row: (
        row.get('semester') or 0,
        (row.get('shift') or ''),
        (row.get('section') or '')
    ))
    return assignments

def get_teacher_attendance_dashboard_summary(teacher_id, on_date=None):
    """Summarize how many assigned teaching groups have attendance recorded on a given day."""
    query = """
        WITH assigned AS (
            SELECT DISTINCT ta.subject_id, ta.class_id
            FROM teacher_assignments ta
            WHERE ta.teacher_id = %s
              AND ta.class_id IS NOT NULL
        ),
        recorded AS (
            SELECT DISTINCT a.subject_id, st.class_id
            FROM attendance a
            JOIN students st ON st.id = a.student_id
            JOIN assigned ass ON ass.subject_id = a.subject_id AND ass.class_id = st.class_id
            WHERE a.date = %s
        )
        SELECT (SELECT COUNT(*) FROM assigned) AS total_groups,
               (SELECT COUNT(*) FROM recorded) AS recorded_groups
    """
    result = execute_query(query, (teacher_id, on_date or date.today().isoformat()), fetch_one=True) or {}
    return {
        'total_groups': result.get('total_groups', 0) or 0,
        'recorded_groups': result.get('recorded_groups', 0) or 0,
    }

def get_teacher_pending_moodle_requests(teacher_id, limit=6):
    """Get Moodle requests for a teacher ordered by due date with pending submission counts."""
    ensure_moodle_assignment_support()
    query = """
        SELECT hw.id AS request_id,
               hw.title,
               hw.due_at,
               hw.due_date,
               s.id AS subject_id,
               s.name AS subject_name,
               c.id AS class_id,
               c.section,
               c.shift,
               c.semester,
               COALESCE(summary.submitted_count, 0) AS submitted_count,
               COALESCE(summary.total_students, 0) AS total_students
        FROM homework hw
        JOIN subjects s ON hw.subject_id = s.id
        JOIN classes c ON hw.class_id = c.id
        LEFT JOIN LATERAL (
            SELECT COUNT(hs.id) AS submitted_count,
                   (
                       SELECT COUNT(*)
                       FROM student_enrollments se
                       JOIN students st ON st.id = se.student_id
                       WHERE se.subject_id = hw.subject_id
                         AND st.class_id = hw.class_id
                   ) AS total_students
            FROM homework_submissions hs
            WHERE hs.homework_id = hw.id
        ) summary ON TRUE
        WHERE hw.teacher_id = %s
          AND COALESCE(hw.is_moodle_request, FALSE) = TRUE
        ORDER BY COALESCE(hw.due_at, hw.due_date::timestamp) ASC, hw.id ASC
        LIMIT %s
    """
    rows = execute_query(query, (teacher_id, limit), fetch_all=True) or []
    for row in rows:
        row['remaining_count'] = max((row.get('total_students') or 0) - (row.get('submitted_count') or 0), 0)
    return rows

def get_teacher_pending_moodle_submission_count(teacher_id):
    """Count remaining Moodle submissions across the teacher's open requests."""
    ensure_moodle_assignment_support()
    query = """
        SELECT COALESCE(SUM(GREATEST(summary.total_students - summary.submitted_count, 0)), 0) AS pending_submission_count
        FROM homework hw
        LEFT JOIN LATERAL (
            SELECT COUNT(hs.id) AS submitted_count,
                   (
                       SELECT COUNT(*)
                       FROM student_enrollments se
                       JOIN students st ON st.id = se.student_id
                       WHERE se.subject_id = hw.subject_id
                         AND st.class_id = hw.class_id
                   ) AS total_students
            FROM homework_submissions hs
            WHERE hs.homework_id = hw.id
        ) summary ON TRUE
        WHERE hw.teacher_id = %s
          AND COALESCE(hw.is_moodle_request, FALSE) = TRUE
    """
    result = execute_query(query, (teacher_id,), fetch_one=True)
    return result['pending_submission_count'] if result else 0

def get_teacher_recent_activity(teacher_id, days=7, limit=8):
    """Get recent student Moodle activity and submissions for a teacher."""
    ensure_student_engagement_support()
    ensure_moodle_assignment_support()
    query = """
        WITH engagement AS (
            SELECT 'engagement' AS activity_type,
                   COALESCE(sess.ended_at, sess.last_ping_at, sess.started_at) AS occurred_at,
                   u.full_name AS student_name,
                   sub.name AS subject_name,
                   c.section,
                   c.shift,
                   COALESCE(sess.resource_title, 'Subject Opened') AS item_title,
                   sess.total_seconds,
                   NULL::VARCHAR AS request_title
            FROM student_engagement_sessions sess
            JOIN students st ON sess.student_id = st.id
            JOIN users u ON st.user_id = u.id
            JOIN subjects sub ON sess.subject_id = sub.id
            JOIN classes c ON sess.class_id = c.id
            JOIN teacher_assignments ta
              ON ta.subject_id = sess.subject_id
             AND ta.class_id = sess.class_id
            WHERE ta.teacher_id = %s
              AND COALESCE(sess.ended_at, sess.last_ping_at, sess.started_at) >= CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
        ),
        submissions AS (
            SELECT 'submission' AS activity_type,
                   hs.updated_at AS occurred_at,
                   u.full_name AS student_name,
                   sub.name AS subject_name,
                   c.section,
                   c.shift,
                   hs.file_name AS item_title,
                   NULL::INTEGER AS total_seconds,
                   hw.title AS request_title
            FROM homework_submissions hs
            JOIN homework hw ON hs.homework_id = hw.id
            JOIN students st ON hs.student_id = st.id
            JOIN users u ON st.user_id = u.id
            JOIN subjects sub ON hw.subject_id = sub.id
            JOIN classes c ON hw.class_id = c.id
            WHERE hw.teacher_id = %s
              AND hs.updated_at >= CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
        )
        SELECT *
        FROM (
            SELECT * FROM engagement
            UNION ALL
            SELECT * FROM submissions
        ) activity
        ORDER BY occurred_at DESC
        LIMIT %s
    """
    return execute_query(query, (teacher_id, days, teacher_id, days, limit), fetch_all=True) or []

def get_homework_by_teacher(teacher_id):
    """Get all homework created by a teacher (with file information)"""
    ensure_moodle_assignment_support()
    query = """
        SELECT h.*, s.name as subject_name, c.name as class_name
        FROM homework h
        JOIN subjects s ON h.subject_id = s.id
        JOIN classes c ON h.class_id = c.id
        WHERE h.teacher_id = %s
          AND COALESCE(h.is_moodle_request, FALSE) = FALSE
        ORDER BY h.due_date DESC
    """
    return execute_query(query, (teacher_id,), fetch_all=True)

def get_timetable_by_teacher(teacher_id):
    """Get timetable for a teacher"""
    query = """
        SELECT tt.*, s.name as subject_name, c.name as class_name
        FROM timetable tt
        JOIN subjects s ON tt.subject_id = s.id
        JOIN classes c ON tt.class_id = c.id
        WHERE tt.teacher_id = %s
        ORDER BY 
            CASE tt.day_of_week
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END,
            tt.start_time
    """
    return execute_query(query, (teacher_id,), fetch_all=True)

def get_lecture_files_by_teacher(teacher_id):
    """Get all lecture files uploaded by a teacher"""
    query = """
        SELECT lf.*, s.name as subject_name, c.name as class_name
        FROM lecture_files lf
        JOIN subjects s ON lf.subject_id = s.id
        LEFT JOIN classes c ON lf.class_id = c.id
        WHERE lf.teacher_id = %s
        ORDER BY lf.uploaded_at DESC
    """
    return execute_query(query, (teacher_id,), fetch_all=True)

def get_teacher_assignments(teacher_id):
    """Get all subject assignments for a teacher"""
    ensure_teacher_assignment_support()
    query = """
        SELECT ta.*,
               s.name AS subject_name,
               c.year,
               c.semester,
               c.section,
               c.shift
        FROM teacher_assignments ta
        JOIN subjects s ON ta.subject_id = s.id
        LEFT JOIN classes c ON ta.class_id = c.id
        WHERE ta.teacher_id = %s
        ORDER BY c.year NULLS LAST, c.semester NULLS LAST, c.section NULLS LAST, s.name
    """
    return execute_query(query, (teacher_id,), fetch_all=True)

def assign_teacher_to_subject(teacher_id, subject_id, class_id, teacher_type='theoretical'):
    """Assign a teacher to teach a subject for a specific class"""
    ensure_teacher_assignment_support()
    # Get shift from class
    class_info = execute_query(
        "SELECT shift FROM classes WHERE id = %s",
        (class_id,),
        fetch_one=True
    )
    if not class_info:
        return None
    
    query = """
        INSERT INTO teacher_assignments (teacher_id, subject_id, class_id, shift, teacher_type)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (teacher_id, subject_id, class_id) DO UPDATE SET teacher_type = EXCLUDED.teacher_type
        RETURNING id
    """
    return execute_insert_returning(query, (teacher_id, subject_id, class_id, class_info['shift'], teacher_type))

def remove_teacher_assignment(assignment_id):
    """Remove a teacher assignment"""
    query = "DELETE FROM teacher_assignments WHERE id = %s"
    return execute_query(query, (assignment_id,))

def get_teachers_for_subject(subject_id, class_id=None):
    """Get all teachers assigned to a subject"""
    query = """
        SELECT ta.*, t.id as teacher_id, u.full_name as teacher_name,
               c.year, c.semester, c.section, c.shift
        FROM teacher_assignments ta
        JOIN teachers t ON ta.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        JOIN classes c ON ta.class_id = c.id
        WHERE ta.subject_id = %s
    """
    params = [subject_id]
    if class_id:
        query += " AND ta.class_id = %s"
        params.append(class_id)
    query += " ORDER BY c.semester, c.section"
    return execute_query(query, tuple(params), fetch_all=True)

def get_teacher_sections(teacher_id, year, semester, shift):
    """Get all sections a teacher teaches for a year/semester/shift"""
    # Get distinct sections where students exist
    query = """
        SELECT DISTINCT s.section
        FROM students s
        WHERE s.year = %s AND s.shift = %s AND s.section IS NOT NULL
        ORDER BY s.section
    """
    # For year 1, semester is 1 or 2; for year 2, semester is 3 or 4
    return execute_query(query, (year, shift), fetch_all=True)

def get_teacher_current_context(teacher_id):
    """Get teacher's assigned subjects grouped by year/shift"""
    query = """
        SELECT ta.shift, ss.year, ss.semester, ss.id as subject_id, ss.name as subject_name,
               (SELECT COUNT(DISTINCT s.section) FROM students s 
                WHERE s.year = ss.year AND s.shift = ta.shift AND s.section IS NOT NULL) as section_count
        FROM teacher_assignments ta
        JOIN semester_subjects ss ON ta.subject_id = ss.id
        WHERE ta.teacher_id = %s
        ORDER BY ss.year, ss.semester, ta.shift, ss.name
    """
    return execute_query(query, (teacher_id,), fetch_all=True)

def get_teacher_schedule_from_builder(teacher_name, major_id=None):
    """Get a teacher's schedule entries from the class_schedules builder data.
    Searches schedules for this major (or all if major_id is None) for entries matching teacher name."""
    import json

    if major_id is not None:
        query = """
            SELECT semester, shift, section, schedule_data
            FROM class_schedules
            WHERE schedule_data IS NOT NULL AND major_id = %s
        """
        rows = execute_query(query, (major_id,), fetch_all=True)
    else:
        query = """
            SELECT semester, shift, section, schedule_data
            FROM class_schedules
            WHERE schedule_data IS NOT NULL
        """
        rows = execute_query(query, fetch_all=True)
    if not rows:
        return []
    
    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    teacher_entries = []
    teacher_lower = teacher_name.lower().strip()
    
    for row in rows:
        data = row['schedule_data']
        if isinstance(data, str):
            data = json.loads(data)
        if not data:
            continue
            
        for entry in data:
            if entry.get('isBreak'):
                continue
            # Check if teacher matches in theory or practical teacher fields
            entry_teacher = (entry.get('teacher') or '').lower().strip()
            practical_teacher = (entry.get('practicalTeacher') or '').lower().strip()
            
            if teacher_lower in (entry_teacher, practical_teacher) or \
               entry_teacher == teacher_lower or practical_teacher == teacher_lower:
                col = entry.get('col', 0)
                day = day_names[col] if col < len(day_names) else f'Day {col}'
                
                # Determine time based on lecture type
                lecture_type = entry.get('lectureType', 'theory')
                if lecture_type == 'practical':
                    start_time = entry.get('practicalStartTime') or entry.get('startTime', '')
                    end_time = entry.get('practicalEndTime') or entry.get('endTime', '')
                else:
                    start_time = entry.get('theoryStartTime') or entry.get('startTime', '')
                    end_time = entry.get('theoryEndTime') or entry.get('endTime', '')
                
                teacher_entries.append({
                    'day_of_week': day,
                    'start_time': start_time,
                    'end_time': end_time,
                    'subject_name': entry.get('subject', ''),
                    'lecture_type': lecture_type,
                    'room': entry.get('room', ''),
                    'semester': row['semester'],
                    'shift': row['shift'],
                    'section': row['section'],
                    'class_label': f"Sem {row['semester']} - {row['shift'].title()} - Class {row['section']}"
                })
    
    # Sort by day order, then start_time
    day_order = {d: i for i, d in enumerate(day_names)}
    teacher_entries.sort(key=lambda x: (day_order.get(x['day_of_week'], 99), x['start_time']))
    
    return teacher_entries

def get_feedback_teacher_subjects(teacher_id):
    """Get all subjects this teacher has been evaluated on"""
    query = """
        SELECT DISTINCT s.id as subject_id, s.name as subject_name
        FROM feedback_responses r
        JOIN subjects s ON r.subject_id = s.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
        ORDER BY s.name
    """
    return execute_query(query, (teacher_id,), fetch_all=True) or []

def get_feedback_teacher_classes(teacher_id, subject_id, major_id=None):
    period = get_latest_feedback_period(major_id)
    curr_year = period.get('study_year')
    curr_sem = period.get('semester')

    query = '''
        SELECT class_id, class_name FROM (
            SELECT c.id as class_id, c.name as class_name
            FROM feedback_responses r
            JOIN classes c ON r.snapshot_class_id = c.id
            JOIN feedback_forms f ON r.form_id = f.id
            WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
              AND r.subject_id = %s
              AND f.study_year = %s
              AND cast(f.semester as text) = cast(%s as text)
            UNION
            SELECT c.id as class_id, c.name as class_name
            FROM student_enrollments se
            JOIN students st ON se.student_id = st.id
            JOIN classes c ON st.class_id = c.id
            WHERE se.subject_id = %s
        ) as combined
        ORDER BY class_name
    '''
    
    return execute_query(query, (teacher_id, subject_id, curr_year, str(curr_sem), subject_id), fetch_all=True) or []

def get_feedback_teacher_detail_current(teacher_id, subject_id, class_id=None, major_id=None):
    """Get student details for teacher/subject/class specifically for the currently active period (includes unenrolled)"""
    import json
    
    # Match the semester for the subject being taught
    subj = execute_query("SELECT semester FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
    subj_sem = str(subj['semester']) if subj else None
    
    query_form = "SELECT study_year, semester FROM feedback_forms WHERE cast(semester as text) = %s "
    params_form = [subj_sem]
    if major_id:
        query_form += " AND created_by IN (SELECT id FROM users WHERE major_id = %s) "
        params_form.append(major_id)
    query_form += " ORDER BY created_at DESC LIMIT 1"
    
    period = execute_query(query_form, tuple(params_form), fetch_one=True)
    if period:
        curr_year = period['study_year']
        curr_sem = period['semester']
    else:
        period = get_latest_feedback_period(major_id)
        curr_year = period.get('study_year')
        curr_sem = period.get('semester')
    
    query = """
        SELECT DISTINCT ON (u.full_name)
            u.full_name as student_name, 
            r.ratings, r.comments, r.submitted_at,
            (SELECT questions FROM feedback_forms WHERE study_year = %s AND cast(semester as text) = cast(%s as text) LIMIT 1) as questions
        FROM students st
        JOIN users u ON st.user_id = u.id
        JOIN student_enrollments se ON st.id = se.student_id
        LEFT JOIN feedback_responses r ON st.id = r.student_id 
             AND r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
             AND r.subject_id = %s
             AND r.form_id IN (SELECT id FROM feedback_forms WHERE study_year = %s AND cast(semester as text) = cast(%s as text))
        WHERE se.subject_id = %s AND cast(st.semester as text) = cast(%s as text)
    """
    params = [curr_year, str(curr_sem) if curr_sem else None, teacher_id, subject_id, curr_year, str(curr_sem) if curr_sem else None, subject_id, subj_sem]
    
    if class_id:
        query += " AND st.class_id = %s "
        params.append(class_id)
        
    query += " ORDER BY u.full_name ASC, r.submitted_at DESC NULLS LAST "
    
    rows = execute_query(query, tuple(params), fetch_all=True) or []
    
    students = []
    questions_list = []
    
    for r in rows:
        rtgs = r['ratings']
        if type(rtgs) == str:
            rtgs = json.loads(rtgs)
            
        if not questions_list and r['questions']:
            q_data = r['questions']
            if type(q_data) == str:
                q_data = json.loads(q_data)
            if isinstance(q_data, list):
                questions_list = [q.get('text', str(q)) if isinstance(q, dict) else str(q) for q in q_data]
                
        student_score = 0
        student_count = 0
        answers = []
        
        if rtgs:
            if isinstance(rtgs, dict):
                for idx_str, v in rtgs.items():
                    if str(v).isdigit():
                        idx_val = -1
                        st_idx = str(idx_str)
                        if st_idx.isdigit(): idx_val = int(st_idx)
                        elif st_idx.startswith('q') and st_idx[1:].isdigit(): idx_val = int(st_idx[1:]) - 1
                        else: idx_val = 0
                        answers.append({'index': idx_val, 'value': int(v)})
                        student_score += int(v)
                        student_count += 1
            elif isinstance(rtgs, list):
                for idx, v in enumerate(rtgs):
                    if str(v).isdigit():
                        answers.append({'index': idx, 'value': int(v)})
                        student_score += int(v)
                        student_count += 1
                        
        avg_rating = round(student_score / student_count, 2) if student_count > 0 else "N/A"
        
        display_answers = []
        if questions_list:
            for idx, q_text in enumerate(questions_list):
                val = next((item['value'] for item in answers if item['index'] == idx), 'N/A')
                display_answers.append({'question': q_text, 'rating': val})
        else:
            for pr in answers:
                display_answers.append({'question': f"Question {pr['index'] + 1}", 'rating': pr['value']})
                
        students.append({
            'student_name': r['student_name'] or 'Anonymous',
            'submitted_at': r['submitted_at'],
            'avg_rating': avg_rating,
            'comments': r['comments'] or '',
            'answers': display_answers
        })
        
    return students, questions_list

def get_feedback_teacher_history_by_year(teacher_id, subject_id, class_id=None):
    """Get historical records grouped cleanly strictly by Study Year and Class, including individual student responses"""
    import json
    
    query = """
        SELECT 
            f.study_year, f.questions, f.semester as form_semester,
            c.id as class_id, c.name as class_name, c.semester as class_semester,
            r.ratings, r.comments, r.submitted_at,
            u.full_name as student_name
        FROM feedback_responses r
        JOIN feedback_forms f ON r.form_id = f.id
        LEFT JOIN classes c ON r.snapshot_class_id = c.id
        LEFT JOIN students st ON r.student_id = st.id
        LEFT JOIN users u ON st.user_id = u.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
          AND r.subject_id = %s
    """
    params = [teacher_id, subject_id]
    
    if class_id:
        query += " AND c.id = %s "
        params.append(class_id)
        
    query += " ORDER BY f.study_year DESC, f.semester DESC NULLS LAST, c.semester DESC, c.name ASC, u.full_name ASC, r.submitted_at DESC NULLS LAST"
    
    rows = execute_query(query, tuple(params), fetch_all=True) or []
    
    history = {}
    seen_responses = set()
    
    for r in rows:
        # Deduplicate student responses per cohort (study_year, form_semester, class, student)
        c_id = r['class_id']
        st_name = r['student_name']
        sy = r['study_year'] or 'Unknown Year'
        fs = str(r['form_semester']) if r.get('form_semester') is not None else '?'
        cn = r['class_name'] or 'Unknown Class'
        
        uniq_key = (sy, fs, c_id, st_name)
        if uniq_key in seen_responses:
            continue
        seen_responses.add(uniq_key)
        cohort_name = f"{cn}"
        
        if sy not in history:
            history[sy] = {
                'study_year': sy,
                'total_responses': 0,
                'semesters': {},
                'total_score': 0,
                'total_ratings': 0
            }
            
        grp_yr = history[sy]
        
        if fs not in grp_yr['semesters']:
            grp_yr['semesters'][fs] = {
                'semester': fs,
                'classes': {}
            }
            
        grp_sem = grp_yr['semesters'][fs]
        
        if cohort_name not in grp_sem['classes']:
            grp_sem['classes'][cohort_name] = {
                'cohort_name': cohort_name,
                'class_id': c_id,
                'response_count': 0,
                'class_score': 0,
                'class_rating_cnt': 0,
                'students': []
            }
            
        cls_grp = grp_sem['classes'][cohort_name]
        
        # Parse questions
        q_text_list = []
        if r['questions']:
            q_data = r['questions']
            if type(q_data) == str:
                q_data = json.loads(q_data)
            if isinstance(q_data, list):
                q_text_list = [q.get('text', str(q)) if isinstance(q, dict) else str(q) for q in q_data]
                
        # Parse ratings
        student_score = 0
        student_count = 0
        rtgs = r['ratings']
        answers = []
        
        if rtgs:
            if type(rtgs) == str:
                rtgs = json.loads(rtgs)
            if isinstance(rtgs, dict):
                for idx_str, v in rtgs.items():
                    if str(v).isdigit():
                        idx_val = -1
                        st_idx = str(idx_str)
                        if st_idx.isdigit(): idx_val = int(st_idx)
                        elif st_idx.startswith('q') and st_idx[1:].isdigit(): idx_val = int(st_idx[1:]) - 1
                        else: idx_val = 0
                        answers.append({'index': idx_val, 'value': int(v)})
                        student_score += int(v)
                        student_count += 1
            elif isinstance(rtgs, list):
                for idx, v in enumerate(rtgs):
                    if str(v).isdigit():
                        answers.append({'index': idx, 'value': int(v)})
                        student_score += int(v)
                        student_count += 1
                        
        avg_rating = round(student_score / student_count, 2) if student_count > 0 else "N/A"
        
        display_answers = []
        if q_text_list:
            for idx, q_text in enumerate(q_text_list):
                val = next((item['value'] for item in answers if item['index'] == idx), 'N/A')
                display_answers.append({'question': q_text, 'rating': val})
        else:
            for pr in answers:
                display_answers.append({'question': f"Question {pr['index']+1}", 'rating': pr['value']})
                
        cls_grp['students'].append({
            'student_name': r['student_name'] or 'Unknown Student',
            'submitted_at': r['submitted_at'],
            'avg_rating': avg_rating,
            'comments': r['comments'],
            'answers': display_answers
        })
        
        cls_grp['response_count'] += 1
        cls_grp['class_score'] += student_score
        cls_grp['class_rating_cnt'] += student_count
        
        grp_yr['total_score'] += student_score
        grp_yr['total_ratings'] += student_count
        grp_yr['total_responses'] += 1
        
    for grp_yr in history.values():
        grp_yr['overall_avg'] = round(grp_yr['total_score'] / grp_yr['total_ratings'], 2) if grp_yr['total_ratings'] > 0 else "N/A"
        
        sem_list = []
        for sem_info in grp_yr['semesters'].values():
            cls_list = []
            for c in sem_info['classes'].values():
                c['class_avg'] = round(c['class_score'] / c['class_rating_cnt'], 2) if c['class_rating_cnt'] > 0 else "N/A"
                cls_list.append(c)
            sem_info['classes'] = sorted(cls_list, key=lambda x: x['cohort_name'])
            sem_list.append(sem_info)
        grp_yr['semesters'] = sorted(sem_list, key=lambda x: x['semester'])
        
    return sorted(list(history.values()), key=lambda x: x['study_year'], reverse=True)

def get_feedback_teacher_subjects(teacher_id, study_year=None):
    """Get all subjects this teacher has been evaluated on"""
    import json
    query = """
        SELECT DISTINCT s.id as subject_id, s.name as subject_name, 
               s.semester as subject_semester,
               COUNT(r.id) as response_count
        FROM feedback_responses r
        JOIN subjects s ON r.subject_id = s.id
        JOIN feedback_forms f ON r.form_id = f.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
    """
    params = [teacher_id]
    if study_year:
        query += " AND f.study_year = %s "
        params.append(study_year)
        
    query += " GROUP BY s.id, s.name, s.semester ORDER BY s.semester, s.name"
    rows = execute_query(query, tuple(params), fetch_all=True) or []
    
    for row in rows:
        rat_query = """
            SELECT r.ratings
            FROM feedback_responses r
            JOIN feedback_forms f ON r.form_id = f.id
            WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s) AND r.subject_id = %s
        """
        rat_params = [teacher_id, row['subject_id']]
        if study_year:
            rat_query += " AND f.study_year = %s"
            rat_params.append(study_year)
            
        ratings_data = execute_query(rat_query, tuple(rat_params), fetch_all=True) or []
        
        total_score = 0
        total_count = 0
        for data in ratings_data:
            rtgs = data['ratings']
            if type(rtgs) == str:
                rtgs = json.loads(rtgs)
            if rtgs and isinstance(rtgs, dict):
                for v in rtgs.values():
                    if str(v).isdigit():
                        total_score += int(v)
                        total_count += 1
            elif rtgs and isinstance(rtgs, list):
                for v in rtgs:
                    if str(v).isdigit():
                        total_score += int(v)
                        total_count += 1
                        
        row['overall_avg'] = round(total_score / total_count, 2) if total_count > 0 else "N/A"
        
    return rows

def get_feedback_teacher_detail(teacher_id, subject_id, study_year):
    """Get full details for a teacher, subject and study_year grouped by class"""
    import json
    query = """
        SELECT 
            c.id as class_id, c.name as class_name,
            u.full_name as student_name, r.student_id,
            r.ratings, r.comments, r.submitted_at,
            f.questions
        FROM feedback_responses r
        JOIN feedback_forms f ON r.form_id = f.id
        LEFT JOIN classes c ON r.snapshot_class_id = c.id
        LEFT JOIN students st ON r.student_id = st.id
        LEFT JOIN users u ON st.user_id = u.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
          AND r.subject_id = %s
          AND f.study_year = %s
        ORDER BY c.name, r.submitted_at DESC
    """
    rows = execute_query(query, (teacher_id, subject_id, study_year), fetch_all=True) or []
    
    grouped = {}
    questions_list = []
    
    for r in rows:
        cls_id = r['class_id'] or 0
        cls_name = r['class_name'] or 'No Class / Unknown'
        
        if cls_id not in grouped:
            grouped[cls_id] = {
                'class_id': cls_id,
                'class_name': cls_name,
                'students': [],
                'class_score_sum': 0,
                'class_rating_count': 0,
                'response_count': 0,
                'question_sums': {}
            }
            
        grp = grouped[cls_id]
        grp['response_count'] += 1
        
        rtgs = r['ratings']
        if type(rtgs) == str:
            rtgs = json.loads(rtgs)
            
        student_score_sum = 0
        student_rating_count = 0
        processed_ratings = []
        
        if not questions_list and r['questions']:
            q_data = r['questions']
            if type(q_data) == str:
                q_data = json.loads(q_data)
            if isinstance(q_data, list):
                questions_list = [q.get('text', str(q)) if isinstance(q, dict) else str(q) for q in q_data]
        
        if rtgs:
            if isinstance(rtgs, dict):
                for idx_str, v in rtgs.items():
                    if str(v).isdigit():
                        idx = -1
                        st_idx = str(idx_str)
                        if st_idx.isdigit(): idx = int(st_idx)
                        elif st_idx.startswith('q') and st_idx[1:].isdigit(): idx = int(st_idx[1:]) - 1
                        else: idx = 0
                        val = int(v)
                        student_score_sum += val
                        student_rating_count += 1
                        processed_ratings.append({'index': idx, 'value': val})
            elif isinstance(rtgs, list):
                for idx, v in enumerate(rtgs):
                    if str(v).isdigit():
                        val = int(v)
                        student_score_sum += val
                        student_rating_count += 1
                        processed_ratings.append({'index': idx, 'value': val})
                        
        for pr in processed_ratings:
            idx = pr['index']
            if idx not in grp['question_sums']:
                grp['question_sums'][idx] = {'sum': 0, 'count': 0}
            grp['question_sums'][idx]['sum'] += pr['value']
            grp['question_sums'][idx]['count'] += 1
            
        grp['class_score_sum'] += student_score_sum
        grp['class_rating_count'] += student_rating_count
        
        student_avg = round(student_score_sum / student_rating_count, 2) if student_rating_count > 0 else "N/A"
        
        display_answers = []
        if questions_list:
            for idx, q_text in enumerate(questions_list):
                val = next((item['value'] for item in processed_ratings if item['index'] == idx), None)
                display_answers.append({
                    'question': q_text,
                    'rating': val
                })
        else:
             for idx, pr in enumerate(processed_ratings):
                display_answers.append({
                    'question': f"Question {pr['index'] + 1}",
                    'rating': pr['value']
                })               
                
        grp['students'].append({
            'student_name': r['student_name'] or 'Anonymous Student',
            'submitted_at': r['submitted_at'],
            'overall_avg': student_avg,
            'comments': r['comments'] or "",
            'answers': display_answers,
            'raw_ratings': processed_ratings
        })
        
    classes_data = []    
    for cls_id, grp in grouped.items():
        grp['class_avg'] = round(grp['class_score_sum'] / grp['class_rating_count'], 2) if grp['class_rating_count'] > 0 else "N/A"
        
        per_question_avg = {}
        for idx in range(len(questions_list)):
             if idx in grp['question_sums'] and grp['question_sums'][idx]['count'] > 0:
                  per_question_avg[idx] = round(grp['question_sums'][idx]['sum'] / grp['question_sums'][idx]['count'], 2)
             else:
                  per_question_avg[idx] = "N/A"
        
        grp['per_question_avg'] = per_question_avg
        classes_data.append(grp)
        
    return classes_data, questions_list

def get_feedback_teacher_history(teacher_id, subject_id):
    """Get historical records grouped by study year for a teacher/subject"""
    import json
    query = """
        SELECT 
            f.study_year,
            c.name as class_name, c.semester as class_semester,
            COUNT(r.id) as response_count,
            jsonb_agg(r.ratings) as all_ratings
        FROM feedback_responses r
        JOIN feedback_forms f ON r.form_id = f.id
        LEFT JOIN classes c ON r.snapshot_class_id = c.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
          AND r.subject_id = %s
        GROUP BY f.study_year, c.name, c.semester
        ORDER BY f.study_year DESC
    """
    rows = execute_query(query, (teacher_id, subject_id), fetch_all=True) or []
    
    history = {}
    for r in rows:
        sy = r['study_year'] or 'Unknown Year'
        if sy not in history:
            history[sy] = {
                'study_year': sy,
                'total_responses': 0,
                'classes': [],
                'total_score': 0,
                'total_ratings': 0
            }
            
        grp = history[sy]
        grp['total_responses'] += r['response_count']
        
        class_score = 0
        class_rating_cnt = 0
        
        all_rat = r.pop('all_ratings')
        if all_rat:
            for rtgs in all_rat:
                if type(rtgs) == str:
                    rtgs = json.loads(rtgs)
                if rtgs and isinstance(rtgs, dict):
                    for v in rtgs.values():
                        if str(v).isdigit():
                            class_score += int(v)
                            class_rating_cnt += 1
                elif rtgs and isinstance(rtgs, list):
                    for v in rtgs:
                        if str(v).isdigit():
                            class_score += int(v)
                            class_rating_cnt += 1
                            
        grp['total_score'] += class_score
        grp['total_ratings'] += class_rating_cnt
        
        class_avg = round(class_score / class_rating_cnt, 2) if class_rating_cnt > 0 else "N/A"
        
        grp['classes'].append({
            'class_name': r['class_name'] or 'No Class',
            'semester': r['class_semester'],
            'response_count': r['response_count'],
            'class_avg': class_avg
        })
        
    for grp in history.values():
        grp['overall_avg'] = round(grp['total_score'] / grp['total_ratings'], 2) if grp['total_ratings'] > 0 else "N/A"
        
    return list(history.values())
