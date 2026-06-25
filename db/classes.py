from .core import *
from .core import _cache_get, _cache_set, _cache_delete, CACHE_TTL_LONG
from .upgrade import ensure_moodle_assignment_support

def get_all_classes(major_id=None):
    if major_id: return execute_query("SELECT * FROM classes WHERE major_id=%s ORDER BY year, semester, section, shift", (major_id,), fetch_all=True)
    cached = _cache_get('classes:all')
    if cached is not None: return cached
    result = execute_query("SELECT * FROM classes ORDER BY year, semester, section, shift", fetch_all=True)
    _cache_set('classes:all', result, CACHE_TTL_LONG)
    return result

def find_or_create_class(year, semester, section, shift, major_id=None):
    if major_id: existing = execute_query("SELECT id FROM classes WHERE year=%s AND semester=%s AND section=%s AND shift=%s AND major_id=%s", (year, semester, section, shift, major_id), fetch_one=True)
    else: existing = execute_query("SELECT id FROM classes WHERE year=%s AND semester=%s AND section=%s AND shift=%s", (year, semester, section, shift), fetch_one=True)
    if existing: return existing['id']
    name = f"Year {year} Sem {semester} {section} {shift.capitalize()}"
    return execute_insert_returning("INSERT INTO classes (name, year, semester, section, shift, major_id) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id", (name, year, semester, section, shift, major_id))

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

def get_subject_count_by_class(class_id):
    result = execute_query("SELECT COUNT(*) as count FROM subjects WHERE class_id=%s", (class_id,), fetch_one=True)
    return result['count'] if result else 0

def get_subject_by_name_and_class(name, class_id): return execute_query("SELECT s.*, ta.id as assignment_id, ta.teacher_id FROM subjects s LEFT JOIN teacher_assignments ta ON s.id=ta.subject_id AND ta.class_id=%s WHERE s.name=%s", (class_id, name), fetch_one=True)

def get_subjects_by_class(class_id): return execute_query("SELECT DISTINCT s.*, ta.id as assignment_id, t.id as teacher_id, u.full_name as teacher_name FROM subjects s JOIN teacher_assignments ta ON s.id=ta.subject_id LEFT JOIN teachers t ON ta.teacher_id=t.id LEFT JOIN users u ON t.user_id=u.id WHERE ta.class_id=%s ORDER BY s.name", (class_id,), fetch_all=True)

def get_first_class_for_semester(year, semester):
    result = execute_query("SELECT id FROM classes WHERE year=%s AND semester=%s ORDER BY id LIMIT 1", (year, semester), fetch_one=True)
    return result['id'] if result else None

def get_homework_by_class(class_id):
    """Get all homework for a class"""
    ensure_moodle_assignment_support()
    query = """
        SELECT h.*, s.name as subject_name, u.full_name as teacher_name
        FROM homework h
        JOIN subjects s ON h.subject_id = s.id
        LEFT JOIN teachers t ON h.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE h.class_id = %s
          AND COALESCE(h.is_moodle_request, FALSE) = FALSE
        ORDER BY h.due_date DESC
    """
    return execute_query(query, (class_id,), fetch_all=True)

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
