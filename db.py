"""
Database connection and helper functions for MIS System
"""
import os
import sys

# Ensure PostgreSQL libpq is available for psycopg3
_pg_bin = r"C:\Program Files\PostgreSQL\17\bin"
if os.path.isdir(_pg_bin) and _pg_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _pg_bin + os.pathsep + os.environ.get("PATH", "")

import psycopg
from psycopg_pool import ConnectionPool
from config import config
from datetime import datetime

# =============================================
# CONNECTION POOL
# =============================================
_conninfo = psycopg.conninfo.make_conninfo(
    host=config.DB_HOST,
    port=int(config.DB_PORT),
    dbname=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
)

_pool = ConnectionPool(conninfo=_conninfo, min_size=2, max_size=20, max_idle=300, open=True)

import redis as _redis_lib
import json as _json

_redis = None
try:
    _redis = _redis_lib.Redis(host='localhost', port=6379, db=0, decode_responses=True,
        socket_connect_timeout=1, socket_timeout=1, retry_on_timeout=False, retry_on_error=[])
    _redis.ping()
    print("Redis cache: connected")
except Exception:
    _redis = None
    print("Redis cache: not available — running without cache")

CACHE_TTL = 300
CACHE_TTL_LONG = 600

def _cache_get(key):
    if _redis is None: return None
    try:
        val = _redis.get(key)
        return _json.loads(val) if val else None
    except Exception: return None

def _cache_set(key, value, ttl=CACHE_TTL):
    if _redis is None or value is None: return
    try: _redis.setex(key, ttl, _json.dumps(value, default=str))
    except Exception: pass

def _cache_delete(*keys):
    if _redis is None: return
    try: _redis.delete(*keys)
    except Exception: pass

def get_db_connection():
    try:
        conn = _pool.getconn()
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def return_connection(conn):
    try: _pool.putconn(conn)
    except Exception: pass

def row_to_dict(cursor, row):
    if row is None: return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    conn = get_db_connection()
    if not conn: return [] if fetch_all else None
    try:
        cursor = conn.cursor()
        cursor.execute(query, params) if params is not None else cursor.execute(query)
        result = None
        if fetch_one:
            result = row_to_dict(cursor, cursor.fetchone())
            conn.commit()
        elif fetch_all:
            rows = cursor.fetchall()
            result = [row_to_dict(cursor, r) for r in rows] if rows else []
            conn.commit()
        else:
            conn.commit()
            result = cursor.rowcount
        cursor.close()
        return_connection(conn)
        return result
    except Exception as e:
        print(f"Query error: {e}")
        try: conn.rollback()
        except Exception: pass
        return_connection(conn)
        return [] if fetch_all else None

def execute_insert_returning(query, params=None):
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        result = row_to_dict(cursor, row)
        conn.commit()
        cursor.close()
        return_connection(conn)
        return result['id'] if result else None
    except Exception as e:
        print(f"Insert error: {e}")
        try: conn.rollback()
        except Exception: pass
        return_connection(conn)
        return None

# SYSTEM SETTINGS
def get_current_cycle():
    result = execute_query("SELECT value FROM system_settings WHERE key = 'current_cycle'", fetch_one=True)
    return int(result['value']) if result else 1

def set_current_cycle(cycle):
    execute_query("""INSERT INTO system_settings (key, value, description, updated_at)
        VALUES ('current_cycle', %s, 'Academic cycle', CURRENT_TIMESTAMP)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP""", (str(cycle),))

def get_semester_for_year(year, cycle=None):
    if cycle is None: cycle = get_current_cycle()
    return (1 if cycle == 1 else 2) if year == 1 else (3 if cycle == 1 else 4)

# STUDENT QUERIES
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

# USER QUERIES
def get_user_by_username(username): return execute_query("SELECT * FROM users WHERE username=%s", (username,), fetch_one=True)
def get_user_by_email(email): return execute_query("SELECT * FROM users WHERE email=%s", (email,), fetch_one=True)
def get_user_by_id(user_id): return execute_query("SELECT * FROM users WHERE id=%s", (user_id,), fetch_one=True)

def create_user(username, password_hash, full_name, role, email=None, plain_password=None, major_id=None):
    return execute_insert_returning("INSERT INTO users (username, password_hash, full_name, role, email, plain_password, major_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", (username, password_hash, full_name, role, email, plain_password, major_id))

def get_all_users(major_id=None):
    if major_id: return execute_query("SELECT id, username, full_name, role, email, created_at, password_hash, plain_password FROM users WHERE major_id=%s ORDER BY id", (major_id,), fetch_all=True)
    return execute_query("SELECT id, username, full_name, role, email, created_at, password_hash, plain_password FROM users ORDER BY id", fetch_all=True)

def delete_user(user_id): return execute_query("DELETE FROM users WHERE id=%s", (user_id,))
def update_user(user_id, full_name, email=None): return execute_query("UPDATE users SET full_name=%s, email=%s WHERE id=%s", (full_name, email, user_id))
def update_user_complete(user_id, username, full_name, email, role): return execute_query("UPDATE users SET username=%s, full_name=%s, email=%s, role=%s WHERE id=%s", (username, full_name, email, role, user_id))
def update_user_password(user_id, password_hash, plain_password=None): return execute_query("UPDATE users SET password_hash=%s, plain_password=%s WHERE id=%s", (password_hash, plain_password, user_id))

# CLASS QUERIES
def get_all_classes(major_id=None):
    if major_id: return execute_query("SELECT * FROM classes WHERE major_id=%s ORDER BY year, semester, section, shift", (major_id,), fetch_all=True)
    cached = _cache_get('classes:all')
    if cached is not None: return cached
    result = execute_query("SELECT * FROM classes ORDER BY year, semester, section, shift", fetch_all=True)
    _cache_set('classes:all', result, CACHE_TTL_LONG)
    return result

def get_distinct_student_groups():
    return execute_query("SELECT DISTINCT year, section, shift, semester, CONCAT(year,'|',section,'|',shift,'|',semester) AS group_key FROM students WHERE year IS NOT NULL AND section IS NOT NULL AND shift IS NOT NULL AND semester IS NOT NULL ORDER BY year, semester, section, shift", fetch_all=True)

def find_or_create_class(year, semester, section, shift, major_id=None):
    if major_id: existing = execute_query("SELECT id FROM classes WHERE year=%s AND semester=%s AND section=%s AND shift=%s AND major_id=%s", (year, semester, section, shift, major_id), fetch_one=True)
    else: existing = execute_query("SELECT id FROM classes WHERE year=%s AND semester=%s AND section=%s AND shift=%s", (year, semester, section, shift), fetch_one=True)
    if existing: return existing['id']
    name = f"Year {year} Sem {semester} {section} {shift.capitalize()}"
    return execute_insert_returning("INSERT INTO classes (name, year, semester, section, shift, major_id) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id", (name, year, semester, section, shift, major_id))

def get_class_student_counts(major_id=None):
    if major_id: results = execute_query("SELECT s.semester, s.shift, s.section, COUNT(s.id) as student_count FROM students s JOIN users u ON s.user_id=u.id WHERE s.semester IS NOT NULL AND s.shift IS NOT NULL AND s.section IS NOT NULL AND u.major_id=%s GROUP BY s.semester, s.shift, s.section ORDER BY s.semester, s.shift, s.section", (major_id,), fetch_all=True)
    else: results = execute_query("SELECT s.semester, s.shift, s.section, COUNT(s.id) as student_count FROM students s WHERE s.semester IS NOT NULL AND s.shift IS NOT NULL AND s.section IS NOT NULL GROUP BY s.semester, s.shift, s.section ORDER BY s.semester, s.shift, s.section", fetch_all=True)
    counts = {}
    semester_totals = {1:0, 2:0, 3:0, 4:0}
    for row in results:
        counts[f"{row['semester']}_{row['shift']}_{row['section']}"] = row['student_count']
        semester_totals[row['semester']] += row['student_count']
    return counts, semester_totals

def get_class_by_id(class_id): return execute_query("SELECT * FROM classes WHERE id=%s", (class_id,), fetch_one=True)
def get_active_classes(): return execute_query("SELECT * FROM classes WHERE is_active=true ORDER BY year, semester, section, shift", fetch_all=True)
def get_classes_by_year_semester(year, semester): return execute_query("SELECT * FROM classes WHERE year=%s AND semester=%s ORDER BY section, shift", (year, semester), fetch_all=True)

def create_class(name, year, semester, section, shift, description=None, major_id=None):
    result = execute_insert_returning("INSERT INTO classes (name, year, semester, section, shift, description, major_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", (name, year, semester, section, shift, description, major_id))
    _cache_delete('classes:all')
    return result

def update_class(class_id, name, year, semester, section, shift, description=None, is_active=True): return execute_query("UPDATE classes SET name=%s, year=%s, semester=%s, section=%s, shift=%s, description=%s, is_active=%s WHERE id=%s", (name, year, semester, section, shift, description, is_active, class_id))
def toggle_class_active(class_id, is_active): return execute_query("UPDATE classes SET is_active=%s WHERE id=%s", (is_active, class_id))
def delete_class(class_id): return execute_query("DELETE FROM classes WHERE id=%s", (class_id,))

# TEACHER QUERIES
def create_teacher(user_id, department=None, phone=None): return execute_insert_returning("INSERT INTO teachers (user_id, department, phone) VALUES (%s,%s,%s) RETURNING id", (user_id, department, phone))
def get_teacher_by_user_id(user_id): return execute_query("SELECT t.*, u.full_name, u.username, u.email FROM teachers t JOIN users u ON t.user_id=u.id WHERE t.user_id=%s", (user_id,), fetch_one=True)

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

# STUDENT QUERIES
def create_student(user_id, class_id=None, student_number=None, phone=None): return execute_insert_returning("INSERT INTO students (user_id, class_id, student_number, phone) VALUES (%s,%s,%s,%s) RETURNING id", (user_id, class_id, student_number, phone))
def get_student_by_user_id(user_id): return execute_query("SELECT s.*, u.full_name, u.username, u.email, u.major_id, c.name as class_name FROM students s JOIN users u ON s.user_id=u.id LEFT JOIN classes c ON s.class_id=c.id WHERE s.user_id=%s", (user_id,), fetch_one=True)
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

# STUDENT ENROLLMENT QUERIES
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

def get_enrolled_subjects_for_student(student_id): return execute_query("SELECT s.*, se.enrolled_at FROM student_enrollments se JOIN subjects s ON se.subject_id=s.id WHERE se.student_id=%s ORDER BY s.name", (student_id,), fetch_all=True)

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

# ENROLLMENT PERIODS
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

def is_enrollment_active(semester, major_id=None): return get_active_enrollment_period(semester, major_id) is not None
def delete_enrollment_period(period_id): return execute_query("DELETE FROM enrollment_periods WHERE id=%s", (period_id,))

# EXAM PERIODS & SIGNUPS
def create_exam_period(semester, period_type, start_date, end_date, description, created_by): return execute_insert_returning("INSERT INTO exam_periods (semester, period_type, start_date, end_date, description, created_by) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id", (semester, period_type, start_date, end_date, description, created_by))

def get_all_exam_periods(semester=None, major_id=None):
    query = "SELECT ep.*, u.full_name as created_by_name FROM exam_periods ep LEFT JOIN users u ON ep.created_by=u.id WHERE 1=1"
    params = []
    if semester: query += " AND ep.semester=%s"; params.append(semester)
    if major_id: query += " AND u.major_id=%s"; params.append(major_id)
    return execute_query(query+" ORDER BY ep.semester, ep.period_type, ep.created_at DESC", tuple(params) if params else None, fetch_all=True)

def get_active_exam_period(semester, period_type, major_id=None):
    query = "SELECT ep.* FROM exam_periods ep LEFT JOIN users u ON ep.created_by=u.id WHERE ep.semester=%s AND ep.period_type=%s AND %s BETWEEN ep.start_date AND ep.end_date"
    params = [semester, period_type, datetime.now()]
    if major_id: query += " AND u.major_id=%s"; params.append(major_id)
    return execute_query(query+" ORDER BY ep.created_at DESC LIMIT 1", tuple(params), fetch_one=True)

def delete_exam_period(period_id): return execute_query("DELETE FROM exam_periods WHERE id=%s", (period_id,))

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

def get_exam_eligible_subjects(student_id, exam_type, semester=None):
    enrolled = get_enrolled_subjects_for_student(student_id) or []
    if semester: enrolled = [s for s in enrolled if s.get('semester') == semester]
    eligible = []
    if exam_type == 'final':
        for subj in enrolled:
            midterm = get_student_midterm_score(student_id, subj['id'])
            max_val, score = midterm['total_max'], midterm['total_score']
            normalized = score / max_val * 60 if max_val > 0 else 0
            existing = get_exam_signup(student_id, subj['id'], 'final')
            subj['midterm_score'] = round(score, 1)
            subj['midterm_max'] = round(max_val, 1)
            subj['midterm_normalized'] = round(normalized, 1)
            subj['coursework_score'] = round(score, 1)
            subj['coursework_max'] = round(max_val, 1)
            subj['coursework_normalized'] = round(normalized, 1)
            subj['already_signed_up'] = existing is not None
            subj['eligible'] = normalized >= 20
            eligible.append(subj)
    elif exam_type == 'second_round':
        for subj in enrolled:
            if not subj.get('results_published'): continue
            grades_data = get_student_grades_for_subject(student_id, subj['id']) or []
            if not grades_data: continue
            total_score, total_max = _calc_grade_totals(grades_data)
            percentage = (total_score / total_max * 100) if total_max > 0 else 0
            if percentage >= 60: continue
            existing = get_exam_signup(student_id, subj['id'], 'second_round')
            subj['percentage'] = round(percentage, 1)
            subj['already_signed_up'] = existing is not None
            subj['eligible'] = True
            eligible.append(subj)
    return eligible

def signup_for_exam(student_id, subject_id, exam_type): return execute_insert_returning("INSERT INTO exam_signups (student_id, subject_id, exam_type) VALUES (%s,%s,%s) ON CONFLICT (student_id, subject_id, exam_type) DO NOTHING RETURNING id", (student_id, subject_id, exam_type))
def cancel_exam_signup(student_id, subject_id, exam_type): return execute_query("DELETE FROM exam_signups WHERE student_id=%s AND subject_id=%s AND exam_type=%s", (student_id, subject_id, exam_type))
def get_exam_signup(student_id, subject_id, exam_type): return execute_query("SELECT * FROM exam_signups WHERE student_id=%s AND subject_id=%s AND exam_type=%s", (student_id, subject_id, exam_type), fetch_one=True)

def get_student_exam_signups(student_id, exam_type=None):
    query = "SELECT es.*, s.name as subject_name, s.semester FROM exam_signups es JOIN subjects s ON es.subject_id=s.id WHERE es.student_id=%s"
    params = [student_id]
    if exam_type: query += " AND es.exam_type=%s"; params.append(exam_type)
    return execute_query(query+" ORDER BY es.signed_up_at DESC", tuple(params), fetch_all=True)

def get_exam_signups_for_subject(subject_id, exam_type=None):
    query = "SELECT es.*, u.full_name as student_name, st.student_number FROM exam_signups es JOIN students st ON es.student_id=st.id JOIN users u ON st.user_id=u.id WHERE es.subject_id=%s"
    params = [subject_id]
    if exam_type: query += " AND es.exam_type=%s"; params.append(exam_type)
    return execute_query(query+" ORDER BY u.full_name", tuple(params), fetch_all=True)

# SUBJECT QUERIES
def get_subject_count_by_class(class_id):
    result = execute_query("SELECT COUNT(*) as count FROM subjects WHERE class_id=%s", (class_id,), fetch_one=True)
    return result['count'] if result else 0

def create_subject(name, semester, description=None, credits=6, major_id=None):
    if major_id: existing = execute_query("SELECT id FROM subjects WHERE LOWER(name)=LOWER(%s) AND semester=%s AND major_id=%s", (name, semester, major_id), fetch_one=True)
    else: existing = execute_query("SELECT id FROM subjects WHERE LOWER(name)=LOWER(%s) AND semester=%s", (name, semester), fetch_one=True)
    if existing: return existing['id']
    return execute_insert_returning("INSERT INTO subjects (name, semester, description, credits, major_id) VALUES (%s,%s,%s,%s,%s) RETURNING id", (name, semester, description, credits, major_id))

def get_subject_by_name_and_class(name, class_id): return execute_query("SELECT s.*, ta.id as assignment_id, ta.teacher_id FROM subjects s LEFT JOIN teacher_assignments ta ON s.id=ta.subject_id AND ta.class_id=%s WHERE s.name=%s", (class_id, name), fetch_one=True)
def get_subjects_by_class(class_id): return execute_query("SELECT DISTINCT s.*, ta.id as assignment_id, t.id as teacher_id, u.full_name as teacher_name FROM subjects s JOIN teacher_assignments ta ON s.id=ta.subject_id LEFT JOIN teachers t ON ta.teacher_id=t.id LEFT JOIN users u ON t.user_id=u.id WHERE ta.class_id=%s ORDER BY s.name", (class_id,), fetch_all=True)

def get_subjects_by_teacher(teacher_id):
    results = execute_query("SELECT DISTINCT s.*, c.name as class_name, c.year, c.semester, c.section, c.shift, ta.id as assignment_id, ta.class_id FROM subjects s JOIN teacher_assignments ta ON s.id=ta.subject_id JOIN classes c ON ta.class_id=c.id WHERE ta.teacher_id=%s ORDER BY c.year, c.semester, c.section, s.name", (teacher_id,), fetch_all=True)
    if results: return results
    return execute_query("SELECT DISTINCT s.*, 'Semester '||s.semester AS class_name, NULL::int AS year, s.semester, NULL::varchar AS section, NULL::varchar AS shift, NULL::int AS assignment_id, NULL::int AS class_id FROM subjects s WHERE s.teacher_id=%s ORDER BY s.semester, s.name", (teacher_id,), fetch_all=True)

def get_all_subjects(major_id=None):
    base = "SELECT DISTINCT s.*, c.name as class_name, c.year, c.semester, c.section, c.shift, ta.id as assignment_id, t.id as teacher_id, u.full_name as teacher_name FROM subjects s LEFT JOIN teacher_assignments ta ON s.id=ta.subject_id LEFT JOIN classes c ON ta.class_id=c.id LEFT JOIN teachers t ON ta.teacher_id=t.id LEFT JOIN users u ON t.user_id=u.id"
    if major_id: return execute_query(base+" WHERE s.major_id=%s ORDER BY s.name, c.year, c.semester, c.section", (major_id,), fetch_all=True)
    return execute_query(base+" ORDER BY s.name, c.year, c.semester, c.section", fetch_all=True)

def get_unique_subjects_by_semester(major_id=None):
    if major_id: return execute_query("SELECT DISTINCT s.name, CASE WHEN s.semester IN (1,2) THEN 1 ELSE 2 END AS year, s.semester FROM subjects s WHERE s.semester IS NOT NULL AND s.major_id=%s ORDER BY s.semester, s.name", (major_id,), fetch_all=True)
    return execute_query("SELECT DISTINCT s.name, CASE WHEN s.semester IN (1,2) THEN 1 ELSE 2 END AS year, s.semester FROM subjects s WHERE s.semester IS NOT NULL ORDER BY s.semester, s.name", fetch_all=True)

def get_subjects_grouped_by_semester(major_id=None):
    major_filter = "AND s.major_id = %s" if major_id else ""
    query = f"""SELECT s.id, s.name, s.semester, s.description, s.credits, s.results_published, c.year, c.section,
        ta.id as assignment_id, t.id as teacher_id, u.full_name as teacher_name,
        COALESCE(gw.total_weight,0) AS total_weight, COALESCE(gw.component_count,0) AS component_count
        FROM subjects s LEFT JOIN teacher_assignments ta ON s.id=ta.subject_id LEFT JOIN classes c ON ta.class_id=c.id
        LEFT JOIN teachers t ON ta.teacher_id=t.id LEFT JOIN users u ON t.user_id=u.id
        LEFT JOIN (SELECT subject_id, COUNT(*) AS component_count, SUM(weight_percentage) AS total_weight FROM grade_components GROUP BY subject_id) gw ON s.id=gw.subject_id
        WHERE s.semester IS NOT NULL {major_filter} ORDER BY c.year, s.semester, c.section, s.name"""
    return execute_query(query, (major_id,) if major_id else None, fetch_all=True)

def get_semesters():
    return [{'year':1,'semester':1,'name':'Year 1 - Semester 1'},{'year':1,'semester':2,'name':'Year 1 - Semester 2'},{'year':2,'semester':3,'name':'Year 2 - Semester 3'},{'year':2,'semester':4,'name':'Year 2 - Semester 4'}]

def get_first_class_for_semester(year, semester):
    result = execute_query("SELECT id FROM classes WHERE year=%s AND semester=%s ORDER BY id LIMIT 1", (year, semester), fetch_one=True)
    return result['id'] if result else None

def get_subject_by_id(subject_id): return execute_query("SELECT s.*, s.semester as semester, ta.id as assignment_id, ta.class_id, c.year, c.section, c.shift, t.id as teacher_id, u.full_name as teacher_name FROM subjects s LEFT JOIN teacher_assignments ta ON s.id=ta.subject_id LEFT JOIN classes c ON ta.class_id=c.id LEFT JOIN teachers t ON ta.teacher_id=t.id LEFT JOIN users u ON t.user_id=u.id WHERE s.id=%s", (subject_id,), fetch_one=True)
def update_subject(subject_id, name, semester, description=None, credits=6): return execute_query("UPDATE subjects SET name=%s, semester=%s, description=%s, credits=%s WHERE id=%s", (name, semester, description, credits, subject_id))
def update_subject_teacher(assignment_id, teacher_id): return execute_query("UPDATE teacher_assignments SET teacher_id=%s WHERE id=%s", (teacher_id, assignment_id))
def delete_subject(subject_id): return execute_query("DELETE FROM subjects WHERE id=%s", (subject_id,))

# ATTENDANCE QUERIES
def record_attendance(student_id, subject_id, teacher_id, date, status, notes=None): return execute_insert_returning("INSERT INTO attendance (student_id, subject_id, teacher_id, date, status, notes) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (student_id, subject_id, date) DO UPDATE SET status=EXCLUDED.status, notes=EXCLUDED.notes RETURNING id", (student_id, subject_id, teacher_id, date, status, notes))

def get_attendance_by_student(student_id, semester=None):
    if semester: return execute_query("SELECT a.*, s.name as subject_name FROM attendance a JOIN subjects s ON a.subject_id=s.id WHERE a.student_id=%s AND s.semester=%s ORDER BY a.date DESC", (student_id, semester), fetch_all=True)
    return execute_query("SELECT a.*, s.name as subject_name FROM attendance a JOIN subjects s ON a.subject_id=s.id WHERE a.student_id=%s ORDER BY a.date DESC", (student_id,), fetch_all=True)

def get_attendance_by_subject_date(subject_id, date): return execute_query("SELECT a.*, u.full_name as student_name, st.student_number FROM attendance a JOIN students st ON a.student_id=st.id JOIN users u ON st.user_id=u.id WHERE a.subject_id=%s AND a.date=%s ORDER BY u.full_name", (subject_id, date), fetch_all=True)


def get_attendance_logs(subject_id, student_id=None, date_from=None, date_to=None, status=None):
    """Get attendance logs with filtering"""
    query = """
        SELECT a.*, u.full_name as student_name, st.student_number, s.name as subject_name
        FROM attendance a
        JOIN students st ON a.student_id = st.id
        JOIN users u ON st.user_id = u.id
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.subject_id = %s
    """
    params = [subject_id]
    
    if student_id:
        query += " AND a.student_id = %s"
        params.append(student_id)
    if date_from:
        query += " AND a.date >= %s"
        params.append(date_from)
    if date_to:
        query += " AND a.date <= %s"
        params.append(date_to)
    if status:
        query += " AND a.status = %s"
        params.append(status)
    
    query += " ORDER BY a.date DESC, u.full_name"
    return execute_query(query, tuple(params), fetch_all=True)


def get_attendance_summary(subject_id):
    """Get attendance summary by student for a subject"""
    query = """
        SELECT st.id as student_id, u.full_name as student_name, st.student_number,
               COUNT(*) as total_classes,
               SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
               SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count,
               SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) as late_count,
               SUM(CASE WHEN a.status = 'excused' THEN 1 ELSE 0 END) as excused_count
        FROM attendance a
        JOIN students st ON a.student_id = st.id
        JOIN users u ON st.user_id = u.id
        WHERE a.subject_id = %s
        GROUP BY st.id, u.full_name, st.student_number
        ORDER BY u.full_name
    """
    return execute_query(query, (subject_id,), fetch_all=True)


def get_attendance_dates(subject_id):
    """Get all unique dates for attendance in a subject"""
    query = """
        SELECT DISTINCT date FROM attendance 
        WHERE subject_id = %s ORDER BY date DESC
    """
    return execute_query(query, (subject_id,), fetch_all=True)


# =============================================
# GRADES QUERIES
# =============================================

def add_grade(student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes=None, component_id=None, published=False):
    """Add a grade for a student (default unpublished/draft)"""
    query = """
        INSERT INTO grades (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published))


def upsert_grade(student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, component_id, notes=None, published=False):
    """Update existing grade or insert new one for a student/component combination (default unpublished/draft)"""
    # Check if a grade already exists for this student and component
    check_query = """
        SELECT id FROM grades 
        WHERE student_id = %s AND component_id = %s
        ORDER BY date DESC, id DESC
        LIMIT 1
    """
    existing = execute_query(check_query, (student_id, component_id), fetch_one=True)

    if existing:
        update_query = """
            UPDATE grades 
            SET score = %s, max_score = %s, date = %s, notes = %s, grade_type = %s, title = %s,
                published = CASE WHEN published = TRUE THEN TRUE ELSE %s END
            WHERE id = %s
            RETURNING id
        """
        return execute_insert_returning(update_query, (score, max_score, date, notes, grade_type, title, published, existing['id']))
    else:
        insert_query = """
            INSERT INTO grades (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        return execute_insert_returning(insert_query, (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published))


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


def get_grades_by_subject(subject_id):
    """Get all grades for a subject"""
    query = """
        SELECT g.*, u.full_name as student_name, st.student_number
        FROM grades g
        JOIN students st ON g.student_id = st.id
        JOIN users u ON st.user_id = u.id
        WHERE g.subject_id = %s
        ORDER BY g.date DESC, u.full_name
    """
    return execute_query(query, (subject_id,), fetch_all=True)


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


def publish_grades_for_subject(subject_id, class_id):
    """Publish all draft grades for a specific subject and class"""
    if class_id:
        query = """
            UPDATE grades 
            SET published = TRUE
            WHERE subject_id = %s 
            AND student_id IN (
                SELECT id FROM students WHERE class_id = %s
            )
            AND published = FALSE
        """
        return execute_query(query, (subject_id, class_id))
    else:
        # No class assignment — publish all grades for this subject
        query = """
            UPDATE grades 
            SET published = TRUE
            WHERE subject_id = %s 
            AND published = FALSE
        """
        return execute_query(query, (subject_id,))


def get_unpublished_grade_count(subject_id, class_id):
    """Get count of unpublished grades for a subject/class"""
    if class_id:
        query = """
            SELECT COUNT(*) as count
            FROM grades g
            JOIN students s ON g.student_id = s.id
            WHERE g.subject_id = %s 
            AND s.class_id = %s
            AND g.published = FALSE
        """
        result = execute_query(query, (subject_id, class_id), fetch_one=True)
    else:
        query = """
            SELECT COUNT(*) as count
            FROM grades g
            WHERE g.subject_id = %s 
            AND g.published = FALSE
        """
        result = execute_query(query, (subject_id,), fetch_one=True)
    return result['count'] if result else 0


def toggle_subject_results_published(subject_id, published):
    """Admin: Toggle results visibility for a subject (final transcript)"""
    query = """
        UPDATE subjects 
        SET results_published = %s
        WHERE id = %s
    """
    return execute_query(query, (published, subject_id))


def publish_semester_results(semester):
    """Admin: Publish all subject results for an entire semester"""
    query = """
        UPDATE subjects 
        SET results_published = TRUE
        WHERE semester = %s
    """
    return execute_query(query, (semester,))


def unpublish_semester_results(semester):
    """Admin: Close/unpublish all subject results for an entire semester"""
    query = """
        UPDATE subjects 
        SET results_published = FALSE
        WHERE semester = %s
    """
    return execute_query(query, (semester,))


# =============================================
# HOMEWORK QUERIES
# =============================================

def create_homework(class_id, subject_id, teacher_id, title, description, due_date, filename=None, file_path=None, file_type=None, file_size=None):
    """Create a new homework assignment"""
    query = """
        INSERT INTO homework (class_id, subject_id, teacher_id, title, description, due_date, filename, file_path, file_type, file_size)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (class_id, subject_id, teacher_id, title, description, due_date, filename, file_path, file_type, file_size))


def get_homework_by_class(class_id):
    """Get all homework for a class"""
    query = """
        SELECT h.*, s.name as subject_name, u.full_name as teacher_name
        FROM homework h
        JOIN subjects s ON h.subject_id = s.id
        LEFT JOIN teachers t ON h.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE h.class_id = %s
        ORDER BY h.due_date DESC
    """
    return execute_query(query, (class_id,), fetch_all=True)


def get_homework_by_teacher(teacher_id):
    """Get all homework created by a teacher (with file information)"""
    query = """
        SELECT h.*, s.name as subject_name, c.name as class_name
        FROM homework h
        JOIN subjects s ON h.subject_id = s.id
        JOIN classes c ON h.class_id = c.id
        WHERE h.teacher_id = %s
        ORDER BY h.due_date DESC
    """
    return execute_query(query, (teacher_id,), fetch_all=True)


def delete_homework(homework_id, teacher_id):
    """Delete homework (mark as done) - only the teacher who created it can delete"""
    query = """
        DELETE FROM homework
        WHERE id = %s AND teacher_id = %s
        RETURNING id
    """
    return execute_insert_returning(query, (homework_id, teacher_id))


# =============================================
# GRADE COMPONENTS QUERIES
# =============================================

_SUM_GRADE_TYPES = {'midterm'}


def _normalize_grade_component_type(component_type):
    return (component_type or '').lower().strip()


def _grade_component_label(component_type):
    return _normalize_grade_component_type(component_type).replace('_', ' ').title()


def _safe_grade_number(value):
    return float(value or 0)


def _summarize_component_rows(rows, force_sum=False):
    items = list(rows or [])
    score_sum = sum(_safe_grade_number(item.get('score')) for item in items)
    max_sum = sum(_safe_grade_number(item.get('max_score')) for item in items)
    count = len(items)

    if force_sum or count <= 1:
        return score_sum, max_sum

    return score_sum / count, max_sum / count


def build_grade_summary(rows):
    """Build canonical grade summary and totals for all grade views.

    Rules:
      - Split midterm components are summed.
      - Non-paired quiz/homework/etc. components are averaged by category.
      - Paired categories (report + seminar) sum each side first, then the pair
        counts once as the average of those per-type totals.
    """
    raw_rows = list(rows or [])
    ordered_groups = []
    group_map = {}

    for row in raw_rows:
        item = row.copy() if isinstance(row, dict) else dict(row)
        component_type = _normalize_grade_component_type(item.get('component_type'))
        pair_group = item.get('pair_group')
        item['component_type'] = component_type

        if pair_group is not None:
            group_key = ('pair', pair_group)
            if group_key not in group_map:
                group_map[group_key] = {
                    'pair_group': pair_group,
                    'rows': [],
                    'type_rows': {},
                    'type_order': [],
                }
                ordered_groups.append(group_key)

            group = group_map[group_key]
            group['rows'].append(item)
            if component_type not in group['type_rows']:
                group['type_rows'][component_type] = []
                group['type_order'].append(component_type)
            group['type_rows'][component_type].append(item)
            continue

        group_key = ('single', component_type)
        if group_key not in group_map:
            group_map[group_key] = {
                'component_type': component_type,
                'rows': [],
            }
            ordered_groups.append(group_key)
        group_map[group_key]['rows'].append(item)

    total_score = 0.0
    total_max = 0.0
    display_groups = []

    for group_key in ordered_groups:
        group = group_map[group_key]

        if group_key[0] == 'pair':
            type_totals = []
            pair_scores = []
            pair_maxes = []

            for component_type in group['type_order']:
                type_rows = group['type_rows'][component_type]
                type_score, type_max = _summarize_component_rows(type_rows, force_sum=True)
                pair_scores.append(type_score)
                pair_maxes.append(type_max)
                type_totals.append({
                    'component_type': component_type,
                    'label': _grade_component_label(component_type),
                    'rows': type_rows,
                    'subtotal_score': round(type_score, 1),
                    'subtotal_max': round(type_max, 1),
                })

            type_count = len(type_totals)
            pair_score = (sum(pair_scores) / type_count) if type_count else 0.0
            pair_max = (sum(pair_maxes) / type_count) if type_count else 0.0

            total_score += pair_score
            total_max += pair_max
            display_groups.append({
                'is_paired': True,
                'label': 'Paired Average',
                'pair_group': group['pair_group'],
                'rows': group['rows'],
                'type_totals': type_totals,
                'subtotal_score': round(pair_score, 1),
                'subtotal_max': round(pair_max, 1),
            })
            continue

        component_type = group['component_type']
        subtotal_score, subtotal_max = _summarize_component_rows(
            group['rows'],
            force_sum=component_type in _SUM_GRADE_TYPES
        )

        total_score += subtotal_score
        total_max += subtotal_max
        display_groups.append({
            'is_paired': False,
            'label': _grade_component_label(component_type),
            'component_type': component_type,
            'rows': group['rows'],
            'subtotal_score': round(subtotal_score, 1),
            'subtotal_max': round(subtotal_max, 1),
        })

    return {
        'groups': display_groups,
        'total_score': round(total_score, 1),
        'total_max': round(total_max, 1),
    }


def build_grade_display_groups(rows):
    """Return canonical display groups for grade tables."""
    return build_grade_summary(rows)['groups']


def _calc_grade_totals(rows):
    """Return canonical total score / total max for a grade component set."""
    summary = build_grade_summary(rows)
    return summary['total_score'], summary['total_max']


def get_next_pair_group(subject_id):
    """Return the next available pair_group integer for a subject (1-based)."""
    result = execute_query(
        "SELECT COALESCE(MAX(pair_group), 0) + 1 AS next_pg FROM grade_components WHERE subject_id = %s",
        (subject_id,), fetch_one=True
    )
    return int(result['next_pg']) if result else 1


def add_grade_component(subject_id, component_type, component_name, max_score, weight_percentage, display_order=0, pair_group=None):
    """Add a grade component to a subject's grading rubric"""
    query = """
        INSERT INTO grade_components 
        (subject_id, component_type, component_name, max_score, weight_percentage, display_order, pair_group)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    result = execute_insert_returning(query, (subject_id, component_type, component_name, max_score, weight_percentage, display_order, pair_group))
    _cache_delete(f'gc:{subject_id}')
    return result


def add_paired_components(subject_id, report_name, seminar_name, weight, display_order=0):
    """Add a paired Report+Seminar pair. Both share the same pair_group so their scores
    are averaged for grade calculation and together consume only `weight`% of the budget."""
    pg = get_next_pair_group(subject_id)
    rid = add_grade_component(subject_id, 'report', report_name, weight, weight, display_order, pair_group=pg)
    sid = add_grade_component(subject_id, 'seminar', seminar_name, weight, weight, display_order + 1, pair_group=pg)
    return rid, sid, pg


def get_grade_components_by_subject(subject_id):
    """Get all grade components for a subject, ordered by display_order"""
    key = f'gc:{subject_id}'
    cached = _cache_get(key)
    if cached is not None:
        return cached
    query = """
        SELECT * FROM grade_components
        WHERE subject_id = %s
        ORDER BY display_order, component_type, id
    """
    result = execute_query(query, (subject_id,), fetch_all=True)
    _cache_set(key, result, CACHE_TTL)
    return result


def get_component_count_by_type(subject_id, component_type):
    """Get count of existing components of a specific type for auto-numbering"""
    query = """
        SELECT COUNT(*) as count
        FROM grade_components
        WHERE subject_id = %s AND component_type = %s
    """
    result = execute_query(query, (subject_id, component_type), fetch_one=True)
    return int(result['count']) if result else 0


def update_grade_component(component_id, component_type, component_name, max_score, weight_percentage, display_order):
    """Update an existing grade component"""
    comp = execute_query("SELECT subject_id FROM grade_components WHERE id = %s", (component_id,), fetch_one=True)
    query = """
        UPDATE grade_components
        SET component_type = %s,
            component_name = %s,
            max_score = %s,
            weight_percentage = %s,
            display_order = %s
        WHERE id = %s
        RETURNING id
    """
    result = execute_insert_returning(query, (component_type, component_name, max_score, weight_percentage, display_order, component_id))
    if comp:
        _cache_delete(f'gc:{comp["subject_id"]}')
    return result


def delete_grade_component(component_id):
    """Delete a grade component"""
    comp = execute_query("SELECT subject_id FROM grade_components WHERE id = %s", (component_id,), fetch_one=True)
    query = "DELETE FROM grade_components WHERE id = %s RETURNING id"
    result = execute_insert_returning(query, (component_id,))
    if comp:
        _cache_delete(f'gc:{comp["subject_id"]}')
    return result


def delete_grade_components_by_type(subject_id, component_type):
    """Delete all grade components of a specific type for a subject"""
    query = "DELETE FROM grade_components WHERE subject_id = %s AND component_type = %s RETURNING id"
    return execute_query(query, (subject_id, component_type), fetch_all=True)


def update_grade_components_by_type(subject_id, component_type, new_total_weight):
    """Update weight for all components of a type (redistribute equally)"""
    # Get all components of this type
    components = execute_query(
        "SELECT id, weight_percentage FROM grade_components WHERE subject_id = %s AND component_type = %s ORDER BY id",
        (subject_id, component_type),
        fetch_all=True
    )
    
    if not components:
        return False
    
    count = len(components)
    individual_weight = round(new_total_weight / count, 2)
    
    # Handle rounding
    weights = [individual_weight] * count
    if sum(weights) != new_total_weight:
        weights[-1] = round(new_total_weight - sum(weights[:-1]), 2)
    
    # Update each component
    for i, comp in enumerate(components):
        execute_query(
            "UPDATE grade_components SET weight_percentage = %s, max_score = %s WHERE id = %s",
            (weights[i], weights[i], comp['id']),
            fetch_one=False
        )
    
    return True


def get_subject_total_weight(subject_id):
    """Calculate effective total weight for a subject.
    Paired components (same pair_group) count as ONE component's weight."""
    query = """
        SELECT COALESCE(SUM(weight_percentage), 0) AS total_weight
        FROM (
            SELECT weight_percentage,
                   ROW_NUMBER() OVER (
                       PARTITION BY CASE WHEN pair_group IS NULL THEN id::text
                                         ELSE (subject_id::text || '-' || pair_group::text) END
                       ORDER BY id
                   ) AS rn
            FROM grade_components
            WHERE subject_id = %s
        ) sub
        WHERE rn = 1
    """
    result = execute_query(query, (subject_id,), fetch_one=True)
    return float(result['total_weight']) if result else 0.0


def get_grade_components_summary(subject_id):
    """Get grade components grouped by type with counts"""
    query = """
        SELECT 
            component_type,
            COUNT(*) as count,
            SUM(weight_percentage) as total_weight
        FROM grade_components
        WHERE subject_id = %s
        GROUP BY component_type
        ORDER BY component_type
    """
    return execute_query(query, (subject_id,), fetch_all=True)


def update_component_display_order(component_id, new_order):
    """Update the display order of a single grade component"""
    query = """
        UPDATE grade_components
        SET display_order = %s
        WHERE id = %s
    """
    try:
        execute_query(query, (new_order, component_id))
        return True
    except Exception as e:
        print(f"Error updating display order: {e}")
        return False


def reorder_categories_by_type(subject_id, category_order_list):
    """
    Reorder all components by category position
    category_order_list: list of component_types in desired order
    Each category gets a base order (0, 100, 200...), components within are sequential
    """
    try:
        print(f"Reordering categories for subject {subject_id}")
        print(f"New order: {category_order_list}")
        
        for idx, component_type in enumerate(category_order_list):
            base_order = idx * 100
            print(f"Processing category {component_type} at position {idx} (base_order={base_order})")
            
            # Get all components of this type, ordered by current display_order
            query_get = """
                SELECT id, component_name, display_order FROM grade_components
                WHERE subject_id = %s AND component_type = %s
                ORDER BY display_order, id
            """
            components = execute_query(query_get, (subject_id, component_type), fetch_all=True)
            print(f"  Found {len(components) if components else 0} components")
            
            if components:
                # Update each component with sequential ordering
                for i, comp in enumerate(components):
                    new_order = base_order + i
                    old_order = comp['display_order']
                    print(f"    Updating {comp['component_name']}: {old_order} -> {new_order}")
                    query_update = """
                        UPDATE grade_components
                        SET display_order = %s
                        WHERE id = %s
                    """
                    result = execute_query(query_update, (new_order, comp['id']))
                    print(f"      Update result: {result}")
        
        print("Reordering complete!")
        return True
    except Exception as e:
        print(f"Error reordering categories: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================
# WEEKLY TOPICS QUERIES
# =============================================

def ensure_exam_notes_column():
    """Add note_type column to weekly_topics if it doesn't exist"""
    try:
        execute_query("""
            ALTER TABLE weekly_topics
            ADD COLUMN IF NOT EXISTS note_type VARCHAR(20) DEFAULT 'exam'
        """, fetch_all=False)
    except Exception as e:
        print(f"ensure_exam_notes_column: {e}")


def create_exam_note(class_id, subject_id, teacher_id, note_type, title, description=None, exam_date=None):
    """Create an exam/quiz/report note (replaces create_weekly_topic)"""
    # Use max+1 as sequence so each insert is unique
    seq_row = execute_query(
        "SELECT COALESCE(MAX(week_number), 0) AS mx FROM weekly_topics WHERE subject_id = %s",
        (subject_id,), fetch_one=True
    )
    seq = (seq_row['mx'] if seq_row else 0) + 1
    query = """
        INSERT INTO weekly_topics
            (class_id, subject_id, teacher_id, week_number, topic, description, date_covered, note_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (class_id, subject_id, teacher_id, seq, title, description, exam_date, note_type))


def delete_exam_note(note_id, teacher_id):
    """Delete an exam note by id (teacher must own it)"""
    execute_query(
        "DELETE FROM weekly_topics WHERE id = %s AND teacher_id = %s",
        (note_id, teacher_id), fetch_all=False
    )


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


def get_weekly_topics_by_class(class_id):
    """Get all exam/quiz notes for a class ordered by date"""
    query = """
        SELECT wt.*, s.name as subject_name, u.full_name as teacher_name,
               COALESCE(wt.note_type, 'exam') as note_type
        FROM weekly_topics wt
        JOIN subjects s ON wt.subject_id = s.id
        LEFT JOIN teachers t ON wt.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE wt.class_id = %s
        ORDER BY wt.date_covered ASC NULLS LAST, wt.id DESC
    """
    return execute_query(query, (class_id,), fetch_all=True)


def get_weekly_topics_by_subject(subject_id):
    """Get exam/quiz notes for a subject ordered by date"""
    query = """
        SELECT wt.*, u.full_name as teacher_name,
               COALESCE(wt.note_type, 'exam') as note_type
        FROM weekly_topics wt
        LEFT JOIN teachers t ON wt.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE wt.subject_id = %s
        ORDER BY wt.date_covered ASC NULLS LAST, wt.id DESC
    """
    return execute_query(query, (subject_id,), fetch_all=True)


# =============================================
# TIMETABLE QUERIES
# =============================================

def create_timetable_entry(class_id, subject_id, teacher_id, day_of_week, start_time, end_time, room=None):
    """Create a timetable entry"""
    query = """
        INSERT INTO timetable (class_id, subject_id, teacher_id, day_of_week, start_time, end_time, room)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (class_id, subject_id, teacher_id, day_of_week, start_time, end_time, room))


def get_timetable_by_class(class_id):
    """Get timetable for a class"""
    query = """
        SELECT tt.*, s.name as subject_name, u.full_name as teacher_name
        FROM timetable tt
        JOIN subjects s ON tt.subject_id = s.id
        LEFT JOIN teachers t ON tt.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE tt.class_id = %s
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
    return execute_query(query, (class_id,), fetch_all=True)


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


# =============================================
# LECTURE FILES MANAGEMENT
# =============================================

def create_lecture_file(subject_id, teacher_id, class_id, title, description, file_name, file_path, file_size, file_type, week_number=None):
    """Upload a new lecture file"""
    query = """
        INSERT INTO lecture_files (subject_id, teacher_id, class_id, title, description, file_name, file_path, file_size, file_type, week_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (subject_id, teacher_id, class_id, title, description, file_name, file_path, file_size, file_type, week_number))


def get_lecture_files_by_subject(subject_id):
    """Get all lecture files for a subject"""
    query = """
        SELECT lf.*, u.full_name as teacher_name
        FROM lecture_files lf
        JOIN teachers t ON lf.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE lf.subject_id = %s
        ORDER BY lf.week_number NULLS LAST, lf.uploaded_at DESC
    """
    return execute_query(query, (subject_id,), fetch_all=True)


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


def get_lecture_files_by_class(class_id):
    """Get all lecture files for a class"""
    query = """
        SELECT lf.*, s.name as subject_name, u.full_name as teacher_name
        FROM lecture_files lf
        JOIN subjects s ON lf.subject_id = s.id
        JOIN teachers t ON lf.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE lf.class_id = %s
        ORDER BY s.name, lf.week_number NULLS LAST, lf.uploaded_at DESC
    """
    return execute_query(query, (class_id,), fetch_all=True)


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


# =============================================
# SEMESTER SUBJECTS QUERIES (NEW STRUCTURE)
# =============================================

def get_all_semester_subjects():
    """Get all semester subjects"""
    query = """
        SELECT * FROM semester_subjects
        ORDER BY year, semester, name
    """
    return execute_query(query, fetch_all=True)


def get_semester_subjects(year, semester):
    """Get subjects for a specific year and semester"""
    query = """
        SELECT * FROM semester_subjects
        WHERE year = %s AND semester = %s
        ORDER BY name
    """
    return execute_query(query, (year, semester), fetch_all=True)


def get_semester_subject_by_id(subject_id):
    """Get a semester subject by ID"""
    query = "SELECT * FROM semester_subjects WHERE id = %s"
    return execute_query(query, (subject_id,), fetch_one=True)


def create_semester_subject(name, year, semester, description=None):
    """Create a new semester subject"""
    query = """
        INSERT INTO semester_subjects (name, year, semester, description)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (name, year, semester, description))


# =============================================
# TEACHER ASSIGNMENTS (NEW STRUCTURE)
# =============================================

def get_teacher_assignments(teacher_id):
    """Get all subject assignments for a teacher"""
    query = """
        SELECT ta.*, ss.name as subject_name, ss.year, ss.semester
        FROM teacher_assignments ta
        JOIN semester_subjects ss ON ta.subject_id = ss.id
        WHERE ta.teacher_id = %s
        ORDER BY ss.year, ss.semester, ta.shift
    """
    return execute_query(query, (teacher_id,), fetch_all=True)


def assign_teacher_to_subject(teacher_id, subject_id, class_id, teacher_type='theoretical'):
    """Assign a teacher to teach a subject for a specific class"""
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


# =============================================
# STUDENT QUERIES (UPDATED FOR NEW STRUCTURE)
# =============================================

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


# =============================================
# MAJOR QUERIES
# Majors are the operational units (e.g. MIS, AI, IS).
# Departments/colleges are grouping only — used for display.
# Each user/class/subject belongs to exactly one major.
# =============================================

def get_all_departments():
    """Get all colleges/departments (grouping layer, read-only)."""
    cached = _cache_get('departments:all')
    if cached is not None:
        return cached
    query = "SELECT * FROM departments ORDER BY name"
    result = execute_query(query, fetch_all=True)
    _cache_set('departments:all', result, CACHE_TTL_LONG)
    return result


def get_all_majors(department_id=None):
    """Get all majors, optionally filtered by college/department."""
    cached_key = f'majors:all:{department_id}'
    cached = _cache_get(cached_key)
    if cached is not None:
        return cached
    if department_id:
        query = """
            SELECT m.*, d.name AS college_name, d.code AS college_code,
                   (SELECT COUNT(*) FROM users u WHERE u.major_id = m.id) AS user_count
            FROM majors m
            LEFT JOIN departments d ON m.department_id = d.id
            WHERE m.department_id = %s
            ORDER BY m.name
        """
        result = execute_query(query, (department_id,), fetch_all=True)
    else:
        query = """
            SELECT m.*, d.name AS college_name, d.code AS college_code,
                   (SELECT COUNT(*) FROM users u WHERE u.major_id = m.id) AS user_count
            FROM majors m
            LEFT JOIN departments d ON m.department_id = d.id
            ORDER BY d.name, m.name
        """
        result = execute_query(query, fetch_all=True)
    _cache_set(cached_key, result, CACHE_TTL_LONG)
    return result


def get_major_by_id(major_id):
    """Get a single major by ID."""
    query = """
        SELECT m.*, d.name AS college_name, d.code AS college_code
        FROM majors m
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE m.id = %s
    """
    return execute_query(query, (major_id,), fetch_one=True)


def get_major_by_code(code):
    """Get a major by its 6-digit numeric code."""
    query = """
        SELECT m.*, d.name AS college_name, d.code AS college_code
        FROM majors m
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE m.code = %s
    """
    return execute_query(query, (str(code),), fetch_one=True)


def get_majors_with_admin_status():
    """Get all majors with count of admin users and their names (for superadmin UI)."""
    query = """
        SELECT m.*, d.name AS college_name, d.code AS college_code,
               COUNT(u.id) FILTER (WHERE u.role = 'admin') AS admin_count,
               STRING_AGG(u.full_name, ', ') FILTER (WHERE u.role = 'admin') AS admin_names
        FROM majors m
        LEFT JOIN departments d ON m.department_id = d.id
        LEFT JOIN users u ON u.major_id = m.id AND u.role = 'admin'
        GROUP BY m.id, d.name, d.code
        ORDER BY d.name, m.name
    """
    return execute_query(query, fetch_all=True)


def assign_major_to_user(user_id, major_id):
    """Assign a user to a major."""
    result = execute_query(
        "UPDATE users SET major_id = %s WHERE id = %s", (major_id, user_id)
    )
    return result

# TEACHER VIEW HELPERS
# =============================================

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


# =============================================
# CLASS SCHEDULE QUERIES
# =============================================

def get_schedule(semester, shift, section, major_id=None):
    """Get schedule for a specific major/semester/shift/section"""
    query = """
        SELECT * FROM class_schedules
        WHERE semester = %s AND shift = %s AND section = %s AND major_id = %s
    """
    return execute_query(query, (semester, shift, section, major_id), fetch_one=True)


def get_class_schedule_data(semester, shift, section, major_id=None):
    """Get parsed schedule data for a specific class (for student view)"""
    import json

    schedule = get_schedule(semester, shift, section, major_id=major_id)
    if not schedule or not schedule.get('schedule_data'):
        return None

    data = schedule['schedule_data']
    if isinstance(data, str):
        data = json.loads(data)

    return data


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


def save_schedule(semester, shift, section, schedule_data, major_id=None):
    """Save or update schedule for a major/semester/shift/section"""
    import json
    # Convert to JSON string if needed
    if isinstance(schedule_data, (list, dict)):
        schedule_data = json.dumps(schedule_data)

    query = """
        INSERT INTO class_schedules (major_id, semester, shift, section, schedule_data, updated_at)
        VALUES (%s, %s, %s, %s, %s::jsonb, CURRENT_TIMESTAMP)
        ON CONFLICT (major_id, semester, shift, section)
        DO UPDATE SET schedule_data = EXCLUDED.schedule_data, updated_at = CURRENT_TIMESTAMP
        RETURNING id
    """
    return execute_insert_returning(query, (major_id, semester, shift, section, schedule_data))


def delete_schedule(semester, shift, section, major_id=None):
    """Delete a schedule"""
    query = """
        DELETE FROM class_schedules
        WHERE semester = %s AND shift = %s AND section = %s AND major_id = %s
    """
    return execute_query(query, (semester, shift, section, major_id))


def get_all_schedules():
    """Get all schedules"""
    query = """
        SELECT * FROM class_schedules
        ORDER BY semester, shift, section
    """
    return execute_query(query, fetch_all=True)


# =============================================
# STUDENT UPGRADE / PROMOTION
# =============================================

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


def get_semester_upgrade_preview(semester):
    """Calculate pass/fail for every student in a semester.
    A student passes only if they score >= 60% in EVERY enrolled subject.
    Returns dict with 'passed' and 'failed' student lists.
    """
    # All students in this semester
    students_query = """
        SELECT s.id, s.shift, s.section, s.year, u.full_name, s.student_number
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.semester = %s
        ORDER BY u.full_name
    """
    students = execute_query(students_query, (semester,), fetch_all=True) or []

    passed = []
    failed = []

    for stu in students:
        # Enrolled subjects
        enrolled = execute_query("""
            SELECT sub.id, sub.name, sub.credits
            FROM student_enrollments se
            JOIN subjects sub ON se.subject_id = sub.id
            WHERE se.student_id = %s
        """, (stu['id'],), fetch_all=True) or []

        if not enrolled:
            # No enrollments - cannot evaluate - mark as failed
            failed.append({**dict(stu), 'subjects': [], 'reason': 'No enrollments'})
            continue

        subject_results = []
        all_passed = True

        for subj in enrolled:
            grades = execute_query("""
                SELECT gc.component_type, gc.pair_group, g.score, gc.max_score
                FROM grade_components gc
                LEFT JOIN grades g ON gc.id = g.component_id
                    AND g.student_id = %s AND g.subject_id = %s
                WHERE gc.subject_id = %s
            """, (stu['id'], subj['id'], subj['id']), fetch_all=True) or []

            if not grades:
                subject_results.append({'name': subj['name'], 'percentage': 0, 'passed': False})
                all_passed = False
                continue

            total_score, total_max = _calc_grade_totals(grades)

            pct = (total_score / total_max * 100) if total_max > 0 else 0
            subj_passed = pct >= 60
            subject_results.append({
                'name': subj['name'],
                'percentage': round(pct, 1),
                'passed': subj_passed
            })
            if not subj_passed:
                all_passed = False

        entry = {**dict(stu), 'subjects': subject_results}
        if all_passed:
            passed.append(entry)
        else:
            failed.append(entry)

    return {'passed': passed, 'failed': failed, 'semester': semester}


def execute_semester_upgrade(semester, admin_user_id):
    """Promote all passing students from `semester` to `semester+1`.
    Returns counts: {promoted, failed, graduated}.
    """
    import json
    preview = get_semester_upgrade_preview(semester)
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
                "SELECT id FROM classes WHERE semester=%s AND shift=%s AND section=%s AND is_active=true LIMIT 1",
                (new_sem, stu['shift'], stu['section']), fetch_one=True
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
