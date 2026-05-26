from .core import *

def get_students_by_year_shift_section(year, shift, section):
    return execute_query("SELECT s.*, u.full_name, u.username, u.email FROM students s JOIN users u ON s.user_id = u.id WHERE s.year=%s AND s.shift=%s AND s.section=%s ORDER BY u.full_name", (year, shift, section), fetch_all=True)

def get_students_by_semester(semester, shift, section):
    return execute_query("SELECT s.*, u.full_name, u.username, u.email FROM students s JOIN users u ON s.user_id = u.id WHERE s.semester=%s AND s.shift=%s AND s.section=%s ORDER BY u.full_name", (semester, shift, section), fetch_all=True)

def get_student_count_by_year_shift_section(year, shift, section):
    result = execute_query("SELECT COUNT(*) as count FROM students WHERE year=%s AND shift=%s AND section=%s", (year, shift, section), fetch_one=True)
    return result['count'] if result else 0

def create_student_with_semester(user_id, year, semester, shift, section, student_number=None, phone=None):
    class_id = None
    if semester and shift and section:
        cls = execute_query("SELECT id FROM classes WHERE semester=%s AND shift=%s AND section=%s AND is_active=true LIMIT 1", (semester, shift, section), fetch_one=True)
        if cls: class_id = cls['id']
    return execute_insert_returning("INSERT INTO students (user_id, year, semester, shift, section, student_number, phone, class_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (user_id, year, semester, shift, section, student_number, phone, class_id))

def get_student_counts_by_semester(major_id=None):
    if major_id:
        results = execute_query("SELECT s.semester, s.shift, s.section, COUNT(*) as count FROM students s JOIN users u ON s.user_id=u.id WHERE s.semester IS NOT NULL AND u.major_id=%s GROUP BY s.semester, s.shift, s.section ORDER BY s.semester, s.shift, s.section", (major_id,), fetch_all=True) or []
    else:
        results = execute_query("SELECT semester, shift, section, COUNT(*) as count FROM students WHERE semester IS NOT NULL GROUP BY semester, shift, section ORDER BY semester, shift, section", fetch_all=True) or []
    stats = {1:{'morning':0,'night':0,'total':0}, 2:{'morning':0,'night':0,'total':0}, 3:{'morning':0,'night':0,'total':0}, 4:{'morning':0,'night':0,'total':0}}
    for r in results:
        sem, shift, count = r['semester'], r['shift'], r['count']
        if sem in stats and shift in stats[sem]:
            stats[sem][shift] += count
            stats[sem]['total'] += count
    return stats

def get_distinct_student_groups():
    return execute_query("SELECT DISTINCT year, section, shift, semester, CONCAT(year,'|',section,'|',shift,'|',semester) AS group_key FROM students WHERE year IS NOT NULL AND section IS NOT NULL AND shift IS NOT NULL AND semester IS NOT NULL ORDER BY year, semester, section, shift", fetch_all=True)

def get_class_student_counts(major_id=None):
    if major_id: results = execute_query("SELECT s.semester, s.shift, s.section, COUNT(s.id) as student_count FROM students s JOIN users u ON s.user_id=u.id WHERE s.semester IS NOT NULL AND s.shift IS NOT NULL AND s.section IS NOT NULL AND u.major_id=%s GROUP BY s.semester, s.shift, s.section ORDER BY s.semester, s.shift, s.section", (major_id,), fetch_all=True)
    else: results = execute_query("SELECT s.semester, s.shift, s.section, COUNT(s.id) as student_count FROM students s WHERE s.semester IS NOT NULL AND s.shift IS NOT NULL AND s.section IS NOT NULL GROUP BY s.semester, s.shift, s.section ORDER BY s.semester, s.shift, s.section", fetch_all=True)
    counts = {}
    semester_totals = {1:0, 2:0, 3:0, 4:0}
    for row in results:
        counts[f"{row['semester']}_{row['shift']}_{row['section']}"] = row['student_count']
        semester_totals[row['semester']] += row['student_count']
    return counts, semester_totals

def create_student(user_id, class_id=None, student_number=None, phone=None): return execute_insert_returning("INSERT INTO students (user_id, class_id, student_number, phone) VALUES (%s,%s,%s,%s) RETURNING id", (user_id, class_id, student_number, phone))

def get_students_by_class(class_id): return execute_query("SELECT s.*, u.full_name, u.username, u.email FROM students s JOIN users u ON s.user_id=u.id WHERE s.class_id=%s ORDER BY u.full_name", (class_id,), fetch_all=True)

def get_all_students(): return execute_query("SELECT s.*, u.full_name, u.username, u.email, c.name as class_name, c.year FROM students s JOIN users u ON s.user_id=u.id LEFT JOIN classes c ON s.class_id=c.id ORDER BY u.full_name", fetch_all=True)

def get_student_by_id(student_id): return execute_query("SELECT s.*, u.full_name, u.username, u.email FROM students s JOIN users u ON s.user_id=u.id WHERE s.id=%s", (student_id,), fetch_one=True)

def update_student(student_id, full_name, email, class_id, student_number, phone):
    if class_id:
        class_info = execute_query('SELECT year, semester, shift, section FROM classes WHERE id=%s', (class_id,), fetch_one=True)
        if class_info:
            result = execute_query("UPDATE students SET class_id=%s, student_number=%s, phone=%s, year=%s, semester=%s, shift=%s, section=%s WHERE id=%s", (class_id, student_number, phone, class_info['year'], class_info['semester'], class_info['shift'], class_info['section'], student_id))
        else:
            result = execute_query("UPDATE students SET class_id=%s, student_number=%s, phone=%s WHERE id=%s", (class_id, student_number, phone, student_id))
    else:
        result = execute_query("UPDATE students SET class_id=%s, student_number=%s, phone=%s WHERE id=%s", (class_id, student_number, phone, student_id))
    student = get_student_by_id(student_id)
    if student: execute_query("UPDATE users SET full_name=%s, email=%s WHERE id=%s", (full_name, email, student['user_id']))
    return result

def delete_student(student_id):
    student = get_student_by_id(student_id)
    if student:
        execute_query("DELETE FROM students WHERE id=%s", (student_id,))
        execute_query("DELETE FROM users WHERE id=%s", (student['user_id'],))
        return True
    return False

def get_students_filtered(year=None, class_id=None):
    query = "SELECT s.*, u.full_name, u.username, u.email, c.name as class_name, c.year FROM students s JOIN users u ON s.user_id=u.id LEFT JOIN classes c ON s.class_id=c.id WHERE 1=1"
    params = []
    if year: query += " AND c.year=%s"; params.append(year)
    if class_id: query += " AND s.class_id=%s"; params.append(class_id)
    query += " ORDER BY u.full_name"
    return execute_query(query, tuple(params) if params else None, fetch_all=True)

def get_available_subjects_for_student(student_id, semester=None):
    if semester is None:
        result = execute_query("SELECT semester FROM students WHERE id=%s", (student_id,), fetch_one=True)
        if result and result['semester']: semester = result['semester']
    if semester is None: return []
    major_row = execute_query("SELECT u.major_id FROM students s JOIN users u ON s.user_id=u.id WHERE s.id=%s", (student_id,), fetch_one=True)
    major_id = major_row['major_id'] if major_row else None
    base = """SELECT s.*, CASE WHEN se.id IS NOT NULL THEN true ELSE false END as is_enrolled,
        (SELECT STRING_AGG(u.full_name||' ('||INITCAP(COALESCE(ta.teacher_type,'theoretical'))||')',' / ' ORDER BY COALESCE(ta.teacher_type,'theoretical'))
         FROM teacher_assignments ta JOIN teachers t ON ta.teacher_id=t.id JOIN users u ON t.user_id=u.id WHERE ta.subject_id=s.id) as teacher_names
        FROM subjects s LEFT JOIN student_enrollments se ON se.student_id=%s AND se.subject_id=s.id WHERE s.semester=%s"""
    if major_id: return execute_query(base+" AND s.major_id=%s ORDER BY s.name", (student_id, semester, major_id), fetch_all=True)
    return execute_query(base+" ORDER BY s.name", (student_id, semester), fetch_all=True)

def get_enrolled_subjects_for_student(student_id):
    query = """
        SELECT s.*,
               se.enrolled_at,
               st.class_id,
               c.name AS class_name,
               COALESCE((
                   SELECT STRING_AGG(
                       u.full_name || ' (' || INITCAP(COALESCE(ta.teacher_type, 'theoretical')) || ')',
                       ' / ' ORDER BY COALESCE(ta.teacher_type, 'theoretical')
                   )
                   FROM teacher_assignments ta
                   JOIN teachers t ON ta.teacher_id = t.id
                   JOIN users u ON t.user_id = u.id
                   WHERE ta.subject_id = s.id
                     AND ta.class_id = st.class_id
               ), '') AS teacher_name
        FROM student_enrollments se
        JOIN subjects s ON se.subject_id = s.id
        JOIN students st ON st.id = se.student_id
        LEFT JOIN classes c ON c.id = st.class_id
        WHERE se.student_id = %s
        ORDER BY s.name
    """
    return execute_query(query, (student_id,), fetch_all=True)

def enroll_student_in_subject(student_id, subject_id):
    if execute_query("SELECT id FROM student_enrollments WHERE student_id=%s AND subject_id=%s", (student_id, subject_id), fetch_one=True): return False
    result = execute_query("INSERT INTO student_enrollments (student_id, subject_id) VALUES (%s,%s) RETURNING id", (student_id, subject_id), fetch_one=True)
    return result is not None

def unenroll_student_from_subject(student_id, subject_id):
    execute_query("DELETE FROM student_enrollments WHERE student_id=%s AND subject_id=%s", (student_id, subject_id))
    return True

def get_enrolled_students_for_subject(subject_id, class_id=None):
    query = "SELECT s.*, u.full_name, u.username, u.email, c.name as class_name, se.enrolled_at FROM student_enrollments se JOIN students s ON se.student_id=s.id JOIN users u ON s.user_id=u.id LEFT JOIN classes c ON s.class_id=c.id WHERE se.subject_id=%s"
    params = [subject_id]
    if class_id: query += " AND s.class_id=%s"; params.append(class_id)
    return execute_query(query+" ORDER BY u.full_name", tuple(params), fetch_all=True)

def create_enrollment_period(semester, start_date, end_date, description, created_by): return execute_insert_returning("INSERT INTO enrollment_periods (semester, start_date, end_date, description, created_by) VALUES (%s,%s,%s,%s,%s) RETURNING id", (semester, start_date, end_date, description, created_by))

def get_active_enrollment_period(semester, major_id=None):
    query = "SELECT ep.* FROM enrollment_periods ep LEFT JOIN users u ON ep.created_by=u.id WHERE ep.semester=%s AND %s BETWEEN ep.start_date AND ep.end_date"
    params = [semester, datetime.now()]
    if major_id: query += " AND u.major_id=%s"; params.append(major_id)
    return execute_query(query+" ORDER BY ep.created_at DESC LIMIT 1", tuple(params), fetch_one=True)

def get_all_enrollment_periods(semester=None, major_id=None):
    query = "SELECT ep.*, u.full_name as created_by_name FROM enrollment_periods ep LEFT JOIN users u ON ep.created_by=u.id WHERE 1=1"
    params = []
    if semester: query += " AND ep.semester=%s"; params.append(semester)
    if major_id: query += " AND u.major_id=%s"; params.append(major_id)
    return execute_query(query+" ORDER BY ep.semester, ep.created_at DESC", tuple(params) if params else None, fetch_all=True)

def get_enrollment_period_by_id(period_id, major_id=None):
    query = "SELECT ep.*, u.full_name as created_by_name FROM enrollment_periods ep LEFT JOIN users u ON ep.created_by=u.id WHERE ep.id=%s"
    params = [period_id]
    if major_id:
        query += " AND u.major_id=%s"
        params.append(major_id)
    return execute_query(query, tuple(params), fetch_one=True)

def is_enrollment_active(semester, major_id=None): return get_active_enrollment_period(semester, major_id) is not None

def delete_enrollment_period(period_id): return execute_query("DELETE FROM enrollment_periods WHERE id=%s", (period_id,))

def get_enrollment_period_signup_summary(semester, major_id=None):
    """Summarize which students in a semester have enrolled in at least one subject."""

    query = """
        WITH semester_students AS (
            SELECT st.id AS student_id,
                   u.full_name AS student_name,
                   u.username,
                   st.student_number,
                   st.shift,
                   st.section,
                   st.year,
                   st.semester,
                   c.name AS class_name
            FROM students st
            JOIN users u ON u.id = st.user_id
            LEFT JOIN classes c ON c.id = st.class_id
            WHERE st.semester = %s
        ),
        signup_counts AS (
            SELECT se.student_id,
                   COUNT(*) AS signup_count
            FROM student_enrollments se
            JOIN subjects sub ON sub.id = se.subject_id
            WHERE sub.semester = %s
            GROUP BY se.student_id
        )
        SELECT ss.*,
               COALESCE(sc.signup_count, 0) AS signup_count,
               CASE WHEN COALESCE(sc.signup_count, 0) > 0 THEN TRUE ELSE FALSE END AS is_assigned
        FROM semester_students ss
        LEFT JOIN signup_counts sc ON sc.student_id = ss.student_id
    """
    params = [semester, semester]
    if major_id is not None:
        query = query.replace("WHERE st.semester = %s", "WHERE st.semester = %s AND u.major_id = %s")
        params = [semester, major_id, semester]
    query += " ORDER BY is_assigned DESC, ss.student_name"
    rows = execute_query(query, tuple(params), fetch_all=True) or []
    assigned = [row for row in rows if row.get('is_assigned')]
    pending = [row for row in rows if not row.get('is_assigned')]
    return {
        'total_students': len(rows),
        'assigned_count': len(assigned),
        'pending_count': len(pending),
        'assigned': assigned,
        'pending': pending,
        'all_rows': rows
    }

def get_student_midterm_score(student_id, subject_id):
    """Return the student's non-final coursework total for a subject."""
    rows = execute_query("""
        SELECT gc.component_type, gc.pair_group, COALESCE(g.score, 0) as score, gc.max_score
        FROM grade_components gc
        LEFT JOIN LATERAL (
            SELECT gr.score
            FROM grades gr
            WHERE gr.component_id = gc.id
              AND gr.student_id = %s
              AND gr.subject_id = %s
              AND gr.published = TRUE
            ORDER BY gr.date DESC, gr.id DESC
            LIMIT 1
        ) g ON TRUE
        WHERE gc.subject_id = %s
          AND gc.component_type != 'final'
        ORDER BY gc.display_order, gc.id
    """, (student_id, subject_id, subject_id), fetch_all=True) or []
    total_score, total_max = _calc_grade_totals(rows)
    return {'total_score': total_score, 'total_max': total_max}

def get_student_exam_signups(student_id, exam_type=None):
    query = "SELECT es.*, s.name as subject_name, s.semester FROM exam_signups es JOIN subjects s ON es.subject_id=s.id WHERE es.student_id=%s"
    params = [student_id]
    if exam_type: query += " AND es.exam_type=%s"; params.append(exam_type)
    return execute_query(query+" ORDER BY es.signed_up_at DESC", tuple(params), fetch_all=True)

def get_attendance_by_student(student_id, semester=None):
    if semester: return execute_query("SELECT a.*, s.name as subject_name FROM attendance a JOIN subjects s ON a.subject_id=s.id WHERE a.student_id=%s AND s.semester=%s ORDER BY a.date DESC", (student_id, semester), fetch_all=True)
    return execute_query("SELECT a.*, s.name as subject_name FROM attendance a JOIN subjects s ON a.subject_id=s.id WHERE a.student_id=%s ORDER BY a.date DESC", (student_id,), fetch_all=True)

def get_student_attendance_summary(student_id, semester=None):
    """Get attendance summary by subject for a student, limited to the selected semester when provided."""
    query = """
        SELECT s.id AS subject_id,
               s.name AS subject_name,
               COALESCE((
                   SELECT STRING_AGG(
                       u.full_name || ' (' || INITCAP(COALESCE(ta.teacher_type, 'theoretical')) || ')',
                       ' / ' ORDER BY COALESCE(ta.teacher_type, 'theoretical')
                   )
                   FROM teacher_assignments ta
                   JOIN teachers t ON ta.teacher_id = t.id
                   JOIN users u ON t.user_id = u.id
                   WHERE ta.subject_id = s.id
                     AND (ta.class_id = st.class_id OR ta.class_id IS NULL)
               ), '') AS teacher_name,
               COUNT(*) AS total_records,
               SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) AS present_count,
               SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) AS absent_count,
               SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) AS late_count,
               SUM(CASE WHEN a.status = 'excused' THEN 1 ELSE 0 END) AS excused_count
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        JOIN students st ON a.student_id = st.id
        WHERE a.student_id = %s
    """
    params = [student_id]
    if semester is not None:
        query += " AND s.semester = %s"
        params.append(semester)
    query += """
        GROUP BY s.id, s.name, st.class_id
        ORDER BY s.name
    """
    return execute_query(query, tuple(params), fetch_all=True) or []

def get_student_attendance_log(student_id, semester=None, limit=10):
    """Get recent attendance records with teacher/class context for a student."""
    query = """
        SELECT a.*,
               s.name AS subject_name,
               COALESCE((
                   SELECT STRING_AGG(
                       u.full_name || ' (' || INITCAP(COALESCE(ta.teacher_type, 'theoretical')) || ')',
                       ' / ' ORDER BY COALESCE(ta.teacher_type, 'theoretical')
                   )
                   FROM teacher_assignments ta
                   JOIN teachers t ON ta.teacher_id = t.id
                   JOIN users u ON t.user_id = u.id
                   WHERE ta.subject_id = s.id
                     AND (ta.class_id = st.class_id OR ta.class_id IS NULL)
               ), '') AS teacher_name
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        JOIN students st ON a.student_id = st.id
        WHERE a.student_id = %s
    """
    params = [student_id]
    if semester is not None:
        query += " AND s.semester = %s"
        params.append(semester)
    query += """
        ORDER BY a.date DESC, a.id DESC
        LIMIT %s
    """
    params.append(limit)
    return execute_query(query, tuple(params), fetch_all=True) or []

def get_teacher_unique_student_count(teacher_id):
    """Get the number of unique students taught by a teacher across all subjects & classes."""
    query = """
        SELECT COUNT(DISTINCT st.id) AS unique_students
        FROM teacher_assignments ta
        JOIN student_enrollments se ON se.subject_id = ta.subject_id
        JOIN students st ON st.id = se.student_id AND st.class_id = ta.class_id
        WHERE ta.teacher_id = %s
    """
    res = execute_query(query, (teacher_id,), fetch_one=True)
    return res['unique_students'] if res else 0

def get_teacher_pending_grade_student_count(teacher_id):
    """Count enrolled students assigned to this teacher who still have missing component grades."""
    query = """
        WITH assigned AS (
            SELECT DISTINCT ta.subject_id, ta.class_id
            FROM teacher_assignments ta
            WHERE ta.teacher_id = %s
              AND ta.class_id IS NOT NULL
        ),
        component_counts AS (
            SELECT gc.subject_id, COUNT(*) AS component_count
            FROM grade_components gc
            GROUP BY gc.subject_id
        ),
        enrolled AS (
            SELECT a.subject_id, a.class_id, st.id AS student_id
            FROM assigned a
            JOIN student_enrollments se ON se.subject_id = a.subject_id
            JOIN students st ON st.id = se.student_id
            WHERE st.class_id = a.class_id
        ),
        student_grade_counts AS (
            SELECT e.subject_id,
                   e.class_id,
                   e.student_id,
                   cc.component_count,
                   COUNT(DISTINCT g.component_id) AS graded_component_count
            FROM enrolled e
            JOIN component_counts cc ON cc.subject_id = e.subject_id
            LEFT JOIN grades g
                ON g.subject_id = e.subject_id
               AND g.student_id = e.student_id
               AND g.component_id IS NOT NULL
            GROUP BY e.subject_id, e.class_id, e.student_id, cc.component_count
        )
        SELECT COUNT(*) AS pending_count
        FROM student_grade_counts
        WHERE graded_component_count < component_count
    """
    result = execute_query(query, (teacher_id,), fetch_one=True)
    return result['pending_count'] if result else 0

def get_student_recent_moodle_materials(student_id, semester=None, limit=6):
    """Get the latest Moodle files/links visible to a student in the current class/semester."""
    query = """
        SELECT lf.id AS file_id,
               lf.title,
               lf.file_name,
               lf.file_type,
               lf.is_link,
               lf.link_url,
               lf.uploaded_at,
               sub.id AS subject_id,
               sub.name AS subject_name,
               mw.title AS week_title
        FROM student_enrollments se
        JOIN students st ON st.id = se.student_id
        JOIN subjects sub ON sub.id = se.subject_id
        JOIN lecture_files lf
          ON lf.subject_id = se.subject_id
         AND lf.class_id = st.class_id
        LEFT JOIN moodle_weeks mw ON mw.id = lf.week_id
        WHERE se.student_id = %s
    """
    params = [student_id]
    if semester is not None:
        query += " AND sub.semester = %s"
        params.append(semester)
    query += """
        ORDER BY lf.uploaded_at DESC, lf.id DESC
        LIMIT %s
    """
    params.append(limit)
    return execute_query(query, tuple(params), fetch_all=True) or []

def get_student_pending_moodle_requests(student_id, semester=None, limit=6):
    """Get Moodle requests still awaiting the student's submission."""
    ensure_moodle_assignment_support()
    query = """
        SELECT hw.id AS request_id,
               hw.title,
               hw.description,
               hw.due_at,
               hw.due_date,
               sub.id AS subject_id,
               sub.name AS subject_name,
               mw.title AS week_title
        FROM student_enrollments se
        JOIN students st ON st.id = se.student_id
        JOIN subjects sub ON sub.id = se.subject_id
        JOIN homework hw
          ON hw.subject_id = se.subject_id
         AND hw.class_id = st.class_id
        LEFT JOIN moodle_weeks mw ON mw.id = hw.week_id
        LEFT JOIN LATERAL (
            SELECT hs.id
            FROM homework_submissions hs
            WHERE hs.homework_id = hw.id
              AND hs.student_id = st.id
            ORDER BY hs.updated_at DESC, hs.id DESC
            LIMIT 1
        ) latest_submission ON TRUE
        WHERE se.student_id = %s
          AND COALESCE(hw.is_moodle_request, FALSE) = TRUE
          AND latest_submission.id IS NULL
    """
    params = [student_id]
    if semester is not None:
        query += " AND sub.semester = %s"
        params.append(semester)
    query += """
        ORDER BY COALESCE(hw.due_at, hw.due_date::timestamp) ASC, hw.id ASC
        LIMIT %s
    """
    params.append(limit)
    return execute_query(query, tuple(params), fetch_all=True) or []

def get_grades_by_student(student_id):
    """Get all grades for a student"""
    query = """
        SELECT g.*, s.name as subject_name
        FROM grades g
        JOIN subjects s ON g.subject_id = s.id
        WHERE g.student_id = %s
        ORDER BY g.date DESC
    """
    return execute_query(query, (student_id,), fetch_all=True)

def get_student_grades_for_subject(student_id, subject_id):
    """Get student's grades for a specific subject with component details (only published grades for students)"""
    query = """
        SELECT 
            gc.id as component_id,
            gc.component_type,
            gc.component_name,
            gc.max_score,
            gc.weight_percentage,
            gc.display_order,
            gc.pair_group,
            g.score,
            g.date as grade_date,
            COALESCE(g.published, FALSE) as published
        FROM grade_components gc
        LEFT JOIN LATERAL (
            SELECT gr.score, gr.date, gr.published
            FROM grades gr
            WHERE gr.component_id = gc.id
              AND gr.student_id = %s
              AND gr.subject_id = %s
              AND gr.published = TRUE
            ORDER BY gr.date DESC, gr.id DESC
            LIMIT 1
        ) g ON TRUE
        WHERE gc.subject_id = %s
        ORDER BY gc.display_order, gc.id
    """
    return execute_query(query, (student_id, subject_id, subject_id), fetch_all=True)

def get_student_result_grades_for_subject(student_id, subject_id):
    """Get a student's official result snapshot for a subject.

    Official result rows are visible only when:
      - the subject results were admin-published,
      - the student was enrolled before the publish moment,
      - and the grade row existed on or before that publish moment.
    """
    ensure_results_publication_support()
    query = """
        SELECT
            gc.id as component_id,
            gc.component_type,
            gc.component_name,
            gc.max_score,
            gc.weight_percentage,
            gc.display_order,
            gc.pair_group,
            g.score,
            g.date as grade_date,
            g.updated_at as grade_updated_at,
            COALESCE(g.published, FALSE) as published
        FROM subjects sub
        JOIN student_enrollments se
            ON se.subject_id = sub.id
           AND se.student_id = %s
        JOIN grade_components gc
            ON gc.subject_id = sub.id
        LEFT JOIN LATERAL (
            SELECT
                gr.score,
                gr.date,
                gr.published,
                COALESCE(gr.updated_at, gr.created_at, CURRENT_TIMESTAMP) as updated_at
            FROM grades gr
            WHERE gr.component_id = gc.id
              AND gr.student_id = %s
              AND gr.subject_id = sub.id
              AND gr.published = TRUE
              AND COALESCE(gr.updated_at, gr.created_at, CURRENT_TIMESTAMP) <= sub.results_published_at
            ORDER BY COALESCE(gr.updated_at, gr.created_at, CURRENT_TIMESTAMP) DESC, gr.id DESC
            LIMIT 1
        ) g ON TRUE
        WHERE sub.id = %s
          AND sub.results_published = TRUE
          AND sub.results_published_at IS NOT NULL
          AND se.enrolled_at <= sub.results_published_at
        ORDER BY gc.display_order, gc.id
    """
    return execute_query(query, (student_id, student_id, subject_id), fetch_all=True) or []

def create_student_v2(user_id, year, shift, section=None, student_number=None, phone=None):
    """Create student with year/shift (section assigned later)"""
    query = """
        INSERT INTO students (user_id, year, shift, section, student_number, phone)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (user_id, year, shift, section, student_number, phone))

def update_student_v2(student_id, full_name, email, year, semester, shift, section, student_number, phone):
    """Update student with new structure including semester"""
    query = """
        UPDATE students 
        SET year = %s, semester = %s, shift = %s, section = %s, student_number = %s, phone = %s
        WHERE id = %s
    """
    result = execute_query(query, (year, semester, shift, section, student_number, phone, student_id))
    
    # Also update user info
    student = get_student_by_id(student_id)
    if student:
        query2 = "UPDATE users SET full_name = %s, email = %s WHERE id = %s"
        execute_query(query2, (full_name, email, student['user_id']))
    
    return result

def get_students_by_year_shift(year, shift, section=None):
    """Get students by year and shift, optionally filtered by section"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.year = %s AND s.shift = %s
    """
    params = [year, shift]
    if section:
        query += " AND s.section = %s"
        params.append(section)
    query += " ORDER BY s.section, u.full_name"
    return execute_query(query, tuple(params), fetch_all=True)

def get_students_without_section(year=None, shift=None):
    """Get students not yet assigned to a section"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.section IS NULL
    """
    params = []
    if year:
        query += " AND s.year = %s"
        params.append(year)
    if shift:
        query += " AND s.shift = %s"
        params.append(shift)
    query += " ORDER BY s.year, s.shift, u.full_name"
    return execute_query(query, tuple(params) if params else None, fetch_all=True)

def assign_student_section(student_id, section):
    """Assign a student to a section"""
    query = "UPDATE students SET section = %s WHERE id = %s"
    return execute_query(query, (section, student_id))

def get_all_students_v2(major_id=None):
    """Get all students with new structure fields"""
    if major_id:
        query = """
            SELECT s.*, u.full_name, u.username, u.email
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE u.major_id = %s
            ORDER BY s.year, s.shift, s.section, u.full_name
        """
        return execute_query(query, (major_id,), fetch_all=True)
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.year, s.shift, s.section, u.full_name
    """
    return execute_query(query, fetch_all=True)

def get_student_by_id_v2(student_id):
    """Get student by ID with new structure"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = %s
    """
    return execute_query(query, (student_id,), fetch_one=True)

def get_student_upgrade_history(student_id):
    """Get promotion history for a student (for viewing old semester data)"""
    query = """
        SELECT uh.*, u.full_name as upgraded_by_name
        FROM upgrade_history uh
        LEFT JOIN users u ON uh.upgraded_by = u.id
        WHERE uh.student_id = %s
        ORDER BY uh.upgraded_at DESC
    """
    return execute_query(query, (student_id,), fetch_all=True) or []

def get_student_grades_for_semester(student_id, semester):
    """Get all grades a student had for subjects in a given semester (historical)"""
    query = """
        SELECT sub.name as subject_name, sub.credits,
               gc.component_type, gc.component_name, gc.max_score, gc.weight_percentage,
               g.score
        FROM student_enrollments se
        JOIN subjects sub ON se.subject_id = sub.id
        JOIN classes c ON sub.class_id = c.id
        LEFT JOIN grade_components gc ON gc.subject_id = sub.id
        LEFT JOIN grades g ON g.component_id = gc.id AND g.student_id = %s
        WHERE se.student_id = %s AND c.semester = %s
        ORDER BY sub.name, gc.display_order
    """
    return execute_query(query, (student_id, student_id, semester), fetch_all=True) or []

def get_student_semester_results(student_id, semester):
    """Calculate per-subject results for a student in a given semester.
    Returns list of {subject_name, credits, percentage, letter_grade, passed}.
    """
    enrolled = execute_query("""
        SELECT sub.id, sub.name, sub.credits
        FROM student_enrollments se
        JOIN subjects sub ON se.subject_id = sub.id
        JOIN classes c ON sub.class_id = c.id
        WHERE se.student_id = %s AND c.semester = %s
    """, (student_id, semester), fetch_all=True) or []

    results = []
    for subj in enrolled:
        grades = execute_query("""
            SELECT gc.component_type, gc.pair_group, g.score, gc.max_score
            FROM grade_components gc
            LEFT JOIN grades g ON gc.id = g.component_id
                AND g.student_id = %s AND g.subject_id = %s
            WHERE gc.subject_id = %s
        """, (student_id, subj['id'], subj['id']), fetch_all=True) or []

        total_score, total_max = _calc_grade_totals(grades)
        pct = (total_score / total_max * 100) if total_max > 0 else 0

        if pct >= 90: lg = 'A'
        elif pct >= 80: lg = 'B'
        elif pct >= 70: lg = 'C'
        elif pct >= 60: lg = 'D'
        else: lg = 'F'

        results.append({
            'subject_name': subj['name'],
            'credits': subj.get('credits') or 0,
            'percentage': round(pct, 1),
            'letter_grade': lg,
            'passed': pct >= 60
        })

    return results

def ensure_student_engagement_support():
    """Ensure engagement tracking can store exact access times and per-visit sessions."""
    global _student_engagement_schema_ready
    if _student_engagement_schema_ready:
        return

    conn = get_db_connection()
    if not conn:
        raise RuntimeError('Database connection unavailable')

    try:
        cursor = conn.cursor()
        cursor.execute("""
            ALTER TABLE student_engagement
            ADD COLUMN IF NOT EXISTS last_access_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
        cursor.execute("""
            UPDATE student_engagement
            SET last_access_at = COALESCE(last_access_at, access_date::timestamp, CURRENT_TIMESTAMP)
            WHERE last_access_at IS NULL
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_engagement_sessions (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_ping_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP NULL,
                total_seconds INTEGER NOT NULL DEFAULT 0,
                resource_title VARCHAR(255) NULL,
                resource_type VARCHAR(50) NULL
            )
        """)
        cursor.execute("""
            ALTER TABLE student_engagement_sessions
            ADD COLUMN IF NOT EXISTS resource_title VARCHAR(255)
        """)
        cursor.execute("""
            ALTER TABLE student_engagement_sessions
            ADD COLUMN IF NOT EXISTS resource_type VARCHAR(50)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_engagement_sessions_lookup
            ON student_engagement_sessions(student_id, subject_id, class_id, started_at DESC)
        """)
        cursor.execute("""
            INSERT INTO student_engagement_sessions (student_id, subject_id, class_id, started_at, last_ping_at, ended_at, total_seconds, resource_title, resource_type)
            SELECT se.student_id,
                   se.subject_id,
                   se.class_id,
                   COALESCE(se.last_access_at, se.access_date::timestamp, CURRENT_TIMESTAMP),
                   COALESCE(se.last_access_at, se.access_date::timestamp, CURRENT_TIMESTAMP),
                   COALESCE(se.last_access_at, se.access_date::timestamp, CURRENT_TIMESTAMP),
                   COALESCE(se.time_spent_seconds, 0),
                   NULL,
                   NULL
            FROM student_engagement se
            WHERE NOT EXISTS (
                SELECT 1
                FROM student_engagement_sessions sess
                WHERE sess.student_id = se.student_id
                  AND sess.subject_id = se.subject_id
                  AND sess.class_id = se.class_id
                  AND DATE(sess.started_at) = se.access_date
            )
        """)
        conn.commit()
        cursor.close()
        _student_engagement_schema_ready = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        return_connection(conn)

def get_moodle_requests_for_student(class_id, subject_id, student_id):
    ensure_moodle_assignment_support()
    query = """
        SELECT hw.*,
               sub.id AS submission_id,
               sub.file_name AS submission_file_name,
               sub.file_path AS submission_file_path,
               sub.file_type AS submission_file_type,
               sub.file_size AS submission_file_size,
               sub.submitted_at,
               sub.updated_at AS submission_updated_at
        FROM homework hw
        LEFT JOIN LATERAL (
            SELECT hs.*
            FROM homework_submissions hs
            WHERE hs.homework_id = hw.id
              AND hs.student_id = %s
            ORDER BY hs.updated_at DESC, hs.id DESC
            LIMIT 1
        ) sub ON TRUE
        WHERE hw.class_id = %s
          AND hw.subject_id = %s
          AND COALESCE(hw.is_moodle_request, FALSE) = TRUE
        ORDER BY COALESCE(hw.week_id, 2147483647), COALESCE(hw.due_at, hw.due_date::timestamp) ASC, hw.id ASC
    """
    return execute_query(query, (student_id, class_id, subject_id), fetch_all=True) or []

def get_moodle_request_submission_by_student(request_id, student_id):
    ensure_moodle_assignment_support()
    query = """
        SELECT *
        FROM homework_submissions
        WHERE homework_id = %s AND student_id = %s
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
    """
    return execute_query(query, (request_id, student_id), fetch_one=True)

def record_student_engagement(student_id, subject_id, class_id, active_seconds):
    ensure_student_engagement_support()
    query = """
        INSERT INTO student_engagement (student_id, subject_id, class_id, time_spent_seconds, last_access_at)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (student_id, subject_id, class_id, access_date)
        DO UPDATE SET time_spent_seconds = student_engagement.time_spent_seconds + EXCLUDED.time_spent_seconds,
                      last_access_at = CURRENT_TIMESTAMP
    """
    execute_query(query, (student_id, subject_id, class_id, active_seconds))

def start_student_engagement_session(student_id, subject_id, class_id, resource_title=None, resource_type=None):
    ensure_student_engagement_support()
    query = """
        INSERT INTO student_engagement_sessions (student_id, subject_id, class_id, started_at, last_ping_at, total_seconds, resource_title, resource_type)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (student_id, subject_id, class_id, resource_title, resource_type))

def ping_student_engagement_session(session_id, student_id, active_seconds):
    ensure_student_engagement_support()
    active_seconds = max(int(active_seconds or 0), 0)
    query = """
        UPDATE student_engagement_sessions
        SET total_seconds = total_seconds + %s,
            last_ping_at = CURRENT_TIMESTAMP
        WHERE id = %s
          AND student_id = %s
          AND ended_at IS NULL
    """
    return execute_query(query, (active_seconds, session_id, student_id))

def stop_student_engagement_session(session_id, student_id):
    ensure_student_engagement_support()
    query = """
        UPDATE student_engagement_sessions
        SET total_seconds = total_seconds + GREATEST(0, EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_ping_at))::INTEGER),
            ended_at = CURRENT_TIMESTAMP,
            last_ping_at = CURRENT_TIMESTAMP
        WHERE id = %s
          AND student_id = %s
          AND ended_at IS NULL
    """
    return execute_query(query, (session_id, student_id))

def set_student_engagement_resource(session_id, student_id, resource_title=None, resource_type=None):
    ensure_student_engagement_support()
    query = """
        UPDATE student_engagement_sessions
        SET resource_title = %s,
            resource_type = %s
        WHERE id = %s
          AND student_id = %s
    """
    return execute_query(query, (resource_title, resource_type, session_id, student_id))

def get_top_students_results(semester=None, class_id=None, shift=None):
    """Calculate total published results for all students based on filters."""
    query = """
        SELECT s.id as student_id, u.full_name as student_name, c.name as class_name, 
               s.shift, c.semester as class_semester, s.class_id
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE 1=1
    """
    params = []
    if class_id:
        query += " AND s.class_id = %s"
        params.append(class_id)
    if shift:
        query += " AND s.shift = %s"
        params.append(shift)
        
    students = execute_query(query, tuple(params), fetch_all=True) or []
    
    results = []
    for st in students:
        # Get enrolled subjects for the student
        sub_query = """
            SELECT sub.id, sub.name, sub.credits, sub.semester
            FROM student_enrollments se
            JOIN subjects sub ON se.subject_id = sub.id
            WHERE se.student_id = %s AND sub.results_published = TRUE
        """
        published_subjects = execute_query(sub_query, (st['student_id'],), fetch_all=True) or []
        
        if not published_subjects:
            continue
            
        sem_weighted = 0
        sem_credits_possible = 0
        cum_weighted = 0
        cum_credits_possible = 0
        
        for subj in published_subjects:
            grades_data = get_student_result_grades_for_subject(st['student_id'], subj['id']) or []
            if not grade_rows_have_scores(grades_data):
                continue
                
            total_score, total_max = _calc_grade_totals(grades_data)
            percentage = (total_score / total_max * 100) if total_max > 0 else 0
            
            credits = subj.get('credits') or 0
            weighted_score = percentage * credits / 100
            
            # Cumulative score
            cum_weighted += weighted_score
            cum_credits_possible += credits
            
            # Semester specific
            if not semester or str(subj['semester']) == str(semester):
                sem_weighted += weighted_score
                sem_credits_possible += credits
                
        # We include the student if they have any published subjects (in the target semester, if specified)
        if (semester and sem_credits_possible > 0) or (not semester and cum_credits_possible > 0):
            results.append({
                'student_id': st['student_id'],
                'student_name': st['student_name'],
                'shift': st['shift'],
                'class_name': st['class_name'],
                'semester': semester if semester else st['class_semester'],
                'total_weighted_score': round(sem_weighted, 3),
                'total_credits': sem_credits_possible,
                'cumulative_weighted_score': round(cum_weighted, 3),
                'cumulative_credits': cum_credits_possible
            })
            
    # Sort students by highest total weighted score
    results.sort(key=lambda x: x['total_weighted_score'], reverse=True)
    return results
