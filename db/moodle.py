from .core import *

def create_weekly_topic(class_id, subject_id, teacher_id, week_number, topic, description=None, date_covered=None):
    """Create a weekly topic"""
    query = """
        INSERT INTO weekly_topics (class_id, subject_id, teacher_id, week_number, topic, description, date_covered)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (class_id, subject_id, week_number) 
        DO UPDATE SET topic = EXCLUDED.topic, description = EXCLUDED.description, date_covered = EXCLUDED.date_covered
        RETURNING id
    """
    return execute_insert_returning(query, (class_id, subject_id, teacher_id, week_number, topic, description, date_covered))

def create_lecture_file(subject_id, teacher_id, class_id, title, description, file_name, file_path, file_size, file_type, week_number=None, week_id=None, is_link=False, link_url=None):
    """Upload a new lecture file or link"""
    ensure_file_metadata_support()
    # Fix for links: database wants NOT NULL files, so supply a stub if empty
    if is_link:
        file_name = file_name or "Link"
        file_size = file_size or 0
        file_path = file_path or "link"
        file_type = file_type or "link"
        
    query = """
        INSERT INTO lecture_files (subject_id, teacher_id, class_id, title, description, file_name, file_path, file_size, file_type, week_number, week_id, is_link, link_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (subject_id, teacher_id, class_id, title, description, file_name, file_path, file_size, file_type, week_number, week_id, is_link, link_url))

def get_lecture_file_by_id(file_id):
    """Get a specific lecture file"""
    query = """
        SELECT lf.*, s.name as subject_name, u.full_name as teacher_name
        FROM lecture_files lf
        JOIN subjects s ON lf.subject_id = s.id
        JOIN teachers t ON lf.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE lf.id = %s
    """
    return execute_query(query, (file_id,), fetch_one=True)

def delete_lecture_file(file_id):
    """Delete a lecture file"""
    query = "DELETE FROM lecture_files WHERE id = %s"
    return execute_query(query, (file_id,))

def get_moodle_weeks(class_id, subject_id):
    query = """
        SELECT * FROM moodle_weeks
        WHERE class_id = %s AND subject_id = %s
        ORDER BY display_order ASC, id ASC
    """
    return execute_query(query, (class_id, subject_id), fetch_all=True) or []

def create_moodle_week(class_id, subject_id, teacher_id, title, display_order=0):
    try:
        display_order = int(display_order) if display_order and str(display_order).strip() else 0
    except ValueError:
        display_order = 0
    query = """
        INSERT INTO moodle_weeks (class_id, subject_id, teacher_id, title, display_order)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_query(query, (class_id, subject_id, teacher_id, title, display_order))
    return True

def find_matching_moodle_week(class_id, subject_id, title, display_order, teacher_id=None):
    """Find the latest Moodle week in the target class with the same title/order."""
    query = """
        SELECT *
        FROM moodle_weeks
        WHERE class_id = %s
          AND subject_id = %s
          AND title = %s
          AND COALESCE(display_order, 0) = %s
    """
    params = [class_id, subject_id, title, display_order]
    if teacher_id is not None:
        query += " AND teacher_id = %s"
        params.append(teacher_id)
    query += " ORDER BY id DESC LIMIT 1"
    return execute_query(query, tuple(params), fetch_one=True)

def get_or_create_moodle_week(class_id, subject_id, teacher_id, title, display_order=0):
    """Return a matching Moodle week for the class, creating it when absent."""
    try:
        display_order = int(display_order) if display_order and str(display_order).strip() else 0
    except ValueError:
        display_order = 0

    existing = find_matching_moodle_week(class_id, subject_id, title, display_order, teacher_id=teacher_id)
    if existing:
        return existing

    week_id = execute_insert_returning("""
        INSERT INTO moodle_weeks (class_id, subject_id, teacher_id, title, display_order)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (class_id, subject_id, teacher_id, title, display_order))
    if not week_id:
        return None
    return get_moodle_week_by_id(week_id)

def delete_moodle_week(week_id, teacher_id):
    query = "DELETE FROM moodle_weeks WHERE id = %s AND teacher_id = %s"
    execute_query(query, (week_id, teacher_id))

def get_moodle_week_by_id(week_id, teacher_id=None):
    query = "SELECT * FROM moodle_weeks WHERE id = %s"
    params = [week_id]
    if teacher_id is not None:
        query += " AND teacher_id = %s"
        params.append(teacher_id)
    return execute_query(query, tuple(params), fetch_one=True)

def get_moodle_request_by_id(request_id):
    ensure_moodle_assignment_support()
    query = """
        SELECT hw.*,
               COALESCE(summary.submitted_count, 0) AS submitted_count,
               COALESCE(summary.total_students, 0) AS total_students
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
        WHERE hw.id = %s
          AND COALESCE(hw.is_moodle_request, FALSE) = TRUE
    """
    return execute_query(query, (request_id,), fetch_one=True)

def get_moodle_requests(class_id, subject_id):
    ensure_moodle_assignment_support()
    query = """
        SELECT hw.*,
               COALESCE(summary.submitted_count, 0) AS submitted_count,
               COALESCE(summary.total_students, 0) AS total_students
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
        WHERE hw.class_id = %s
          AND hw.subject_id = %s
          AND COALESCE(hw.is_moodle_request, FALSE) = TRUE
        ORDER BY COALESCE(hw.week_id, 2147483647), COALESCE(hw.due_at, hw.due_date::timestamp) ASC, hw.id ASC
    """
    rows = execute_query(query, (class_id, subject_id), fetch_all=True) or []
    for row in rows:
        row['remaining_count'] = max((row.get('total_students') or 0) - (row.get('submitted_count') or 0), 0)
    return rows

def get_moodle_request_roster(request_id):
    ensure_moodle_assignment_support()
    request_row = get_moodle_request_by_id(request_id)
    if not request_row:
        return []

    query = """
        SELECT st.id AS student_id,
               u.full_name AS student_name,
               u.username,
               se.enrolled_at,
               hs.id AS submission_id,
               hs.file_name,
               hs.file_path,
               hs.file_type,
               hs.file_size,
               hs.submitted_at,
               hs.updated_at
        FROM student_enrollments se
        JOIN students st ON st.id = se.student_id
        JOIN users u ON u.id = st.user_id
        LEFT JOIN LATERAL (
            SELECT sub.*
            FROM homework_submissions sub
            WHERE sub.homework_id = %s
              AND sub.student_id = st.id
            ORDER BY sub.updated_at DESC, sub.id DESC
            LIMIT 1
        ) hs ON TRUE
        WHERE se.subject_id = %s
          AND st.class_id = %s
        ORDER BY CASE WHEN hs.id IS NULL THEN 1 ELSE 0 END, u.full_name
    """
    return execute_query(query, (request_id, request_row['subject_id'], request_row['class_id']), fetch_all=True) or []

def get_moodle_request_submission_by_id(submission_id):
    ensure_moodle_assignment_support()
    query = """
        SELECT hs.*, hw.subject_id, hw.class_id, hw.teacher_id, hw.title AS request_title
        FROM homework_submissions hs
        JOIN homework hw ON hw.id = hs.homework_id
        WHERE hs.id = %s
    """
    return execute_query(query, (submission_id,), fetch_one=True)

def get_moodle_request_submissions(request_id):
    ensure_moodle_assignment_support()
    query = """
        SELECT *
        FROM homework_submissions
        WHERE homework_id = %s
        ORDER BY submitted_at DESC, id DESC
    """
    return execute_query(query, (request_id,), fetch_all=True) or []

def update_moodle_request_due(request_id, teacher_id, due_at):
    ensure_moodle_assignment_support()
    query = """
        UPDATE homework
        SET due_at = %s,
            due_date = DATE(%s)
        WHERE id = %s
          AND teacher_id = %s
          AND COALESCE(is_moodle_request, FALSE) = TRUE
    """
    return execute_query(query, (due_at, due_at, request_id, teacher_id))

def delete_moodle_request(request_id, teacher_id):
    ensure_moodle_assignment_support()
    query = """
        DELETE FROM homework
        WHERE id = %s
          AND teacher_id = %s
          AND COALESCE(is_moodle_request, FALSE) = TRUE
        RETURNING id
    """
    return execute_insert_returning(query, (request_id, teacher_id))

def delete_moodle_requests_by_week(week_id):
    ensure_moodle_assignment_support()
    query = "DELETE FROM homework WHERE week_id = %s AND COALESCE(is_moodle_request, FALSE) = TRUE"
    return execute_query(query, (week_id,))

def upsert_moodle_request_submission(request_id, student_id, file_name, file_path, file_type=None, file_size=0):
    ensure_file_metadata_support()
    ensure_moodle_assignment_support()
    query = """
        INSERT INTO homework_submissions (
            homework_id, student_id, file_name, file_path, file_type, file_size, submitted_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (homework_id, student_id)
        DO UPDATE SET
            file_name = EXCLUDED.file_name,
            file_path = EXCLUDED.file_path,
            file_type = EXCLUDED.file_type,
            file_size = EXCLUDED.file_size,
            submitted_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
    """
    return execute_insert_returning(query, (request_id, student_id, file_name, file_path, file_type, file_size))

def delete_moodle_request_submissions(request_id):
    ensure_moodle_assignment_support()
    query = "DELETE FROM homework_submissions WHERE homework_id = %s"
    return execute_query(query, (request_id,))

def get_moodle_content(class_id, subject_id, student_id=None):
    ensure_moodle_assignment_support()
    weeks = get_moodle_weeks(class_id, subject_id)
    
    query_files = "SELECT * FROM lecture_files WHERE class_id = %s AND subject_id = %s ORDER BY id ASC"
    files = execute_query(query_files, (class_id, subject_id), fetch_all=True) or []
    requests = (
        get_moodle_requests_for_student(class_id, subject_id, student_id)
        if student_id is not None else
        get_moodle_requests(class_id, subject_id)
    )
    content = []
    
    for week in weeks:
        week_data = dict(week)
        week_data['files'] = [f for f in files if f.get('week_id') == week['id']]
        week_data['requests'] = [r for r in requests if r.get('week_id') == week['id']]
        content.append(week_data)
        
    no_week_files = [f for f in files if f.get('week_id') is None]
    no_week_requests = [r for r in requests if r.get('week_id') is None]
    
    if no_week_files or no_week_requests:
        content.append({
            'id': None,
            'title': 'Unassigned',
            'display_order': 9999,
            'files': no_week_files,
            'requests': no_week_requests,
        })
        
    return content

def get_moodle_engagement_stats(subject_id, class_id):
    ensure_student_engagement_support()
    query = """
        SELECT s.id AS student_id,
               u.full_name AS student_name,
               MAX(COALESCE(sess.ended_at, sess.last_ping_at, sess.started_at)) AS last_access_at,
               SUM(sess.total_seconds) AS time_spent_seconds,
               COUNT(DISTINCT DATE(sess.started_at)) AS active_days,
               COUNT(*) AS session_count
        FROM student_engagement_sessions sess
        JOIN students s ON sess.student_id = s.id
        JOIN users u ON s.user_id = u.id
        WHERE sess.subject_id = %s AND sess.class_id = %s
        GROUP BY s.id, u.full_name
        ORDER BY MAX(COALESCE(sess.ended_at, sess.last_ping_at, sess.started_at)) DESC,
                 SUM(sess.total_seconds) DESC
    """
    return execute_query(query, (subject_id, class_id), fetch_all=True) or []

def get_moodle_engagement_daily_details(subject_id, class_id):
    ensure_student_engagement_support()
    query = """
        SELECT sess.id AS session_id,
               s.id AS student_id,
               u.full_name AS student_name,
               DATE(sess.started_at) AS access_date,
               sess.started_at,
               COALESCE(sess.ended_at, sess.last_ping_at, sess.started_at) AS ended_at,
               sess.total_seconds AS time_spent_seconds,
               sess.resource_title,
               sess.resource_type
        FROM student_engagement_sessions sess
        JOIN students s ON sess.student_id = s.id
        JOIN users u ON s.user_id = u.id
        WHERE sess.subject_id = %s AND sess.class_id = %s
        ORDER BY u.full_name, sess.started_at DESC
    """
    return execute_query(query, (subject_id, class_id), fetch_all=True) or []

def update_lecture_file_asset(file_id, teacher_id, file_name, file_path, file_size, file_type):
    ensure_file_metadata_support()
    query = """
        UPDATE lecture_files
        SET file_name = %s,
            file_path = %s,
            file_size = %s,
            file_type = %s,
            is_link = FALSE,
            link_url = NULL
        WHERE id = %s AND teacher_id = %s
    """
    return execute_query(query, (file_name, file_path, file_size, file_type, file_id, teacher_id))

def get_lecture_files_for_week(week_id, teacher_id=None):
    query = "SELECT * FROM lecture_files WHERE week_id = %s"
    params = [week_id]
    if teacher_id is not None:
        query += " AND teacher_id = %s"
        params.append(teacher_id)
    return execute_query(query + " ORDER BY id ASC", tuple(params), fetch_all=True) or []
